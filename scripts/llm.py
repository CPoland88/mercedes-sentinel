"""Claude API wrapper for the C2 triage layer.

Responsibilities:

1. Assemble the system prompt by concatenating the prompt template
   (scripts/prompts/system.md) with the project's living rubric files
   (CONTEXT.md + a curated set of references/*.md). The rubric is
   marked with `cache_control: ephemeral` so Anthropic caches it; on
   subsequent triage calls within ~5 minutes, the cached portion is
   billed at 10% of the normal input rate. For a daily 4 PM batch
   of 3-10 candidates this is the difference between ~$0.50 and
   ~$0.05 per run.

2. Load the tool-use schema from scripts/prompts/triage_tool.json.
   Forcing tool use (`tool_choice={"type": "tool", ...}`) means
   Claude *must* respond by calling that tool with arguments matching
   the schema. We never have to parse free-form JSON or recover from
   "Claude wrote prose instead of JSON."

3. Per-candidate: build the user prompt from the candidate dict and
   the raw email body, call the API, return a parsed verdict dict.

4. Retry on transient errors (rate limit, overloaded, network).
   Raise on auth / schema errors so the caller can decide whether to
   re-queue or mark the candidate NEEDS_HUMAN.

The Anthropic client is constructed lazily so test code can patch
`get_client` to inject a mock without needing ANTHROPIC_API_KEY set
in the environment.

## Per-vehicle profile (scalability hooks)

`RUBRIC_FILES`, `SYSTEM_TEMPLATE_PATH`, and `DEFAULT_MODEL` are the
per-vehicle profile constants. The functions in this module use them
as defaults but accept explicit overrides (`rubric_files=`,
`system_template_path=`, `model=`) so the same infrastructure can
serve multiple vehicle pursuits without a code fork — e.g., a future
umbrella orchestrator that triages Mercedes candidates with the MB
profile and Corvette candidates with a separate profile in the same
Python process. When cloning this repo for a different vehicle,
either (a) edit the three module constants in-place, or (b) leave
them and pass overrides from a per-vehicle config module.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Paths — resolved relative to the repo root (this file's grandparent)
REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_TEMPLATE_PATH = PROMPTS_DIR / "system.md"
TRIAGE_TOOL_PATH = PROMPTS_DIR / "triage_tool.json"

# Files inlined into the cached system prompt. Order is intentional —
# CONTEXT first (highest authority), then the rubric files in roughly
# the order Claude needs them while triaging a candidate.
RUBRIC_FILES = [
    "CONTEXT.md",
    "references/dealer-tier-list.md",
    "references/gls-trim-decoder.md",
    "references/mbusa-cpo-criteria.md",
    "references/comp-pricing-framework.md",
]

# Model + token budget. Sonnet 4.6 is the agreed default; max_tokens is
# the output cap — the structured verdict is small (~400 tokens at
# most), so 2048 is plenty of headroom.
DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_OUTPUT_TOKENS = 2048

# Retry settings for transient API errors
MAX_RETRIES = 3
RETRY_BASE_DELAY_SEC = 2.0


# ---------- prompt assembly ----------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assemble_system_prompt(
    rubric_files: Optional[list] = None,
    system_template_path: Optional[Path] = None,
) -> str:
    """Build the full system prompt: template + rubric concatenation.

    Both arguments default to the module-level constants, which is the
    Mercedes Sentinel profile. Pass overrides when running a different
    vehicle profile through the same triage infrastructure — for
    example, an umbrella orchestrator can call this once per profile
    per batch.
    """
    files = rubric_files if rubric_files is not None else RUBRIC_FILES
    template = (
        system_template_path
        if system_template_path is not None
        else SYSTEM_TEMPLATE_PATH
    )
    parts = [_read(template)]
    for rel_path in files:
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            logger.warning("Rubric file missing, skipping: %s", rel_path)
            continue
        parts.append(f"\n\n## Source: `{rel_path}`\n\n")
        parts.append(_read(full_path))
    return "".join(parts)


def load_triage_tool() -> dict:
    """Load the tool-use schema. Returned dict is in Anthropic's
    expected format and can be passed directly into messages.create()."""
    with open(TRIAGE_TOOL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_user_message(candidate: dict, raw_email_body: Optional[str] = None) -> str:
    """Construct the per-candidate user prompt.

    Includes the structured parser output AND the raw email body when
    available, so Claude can re-verify the parser's metadata against
    the source text (and notice details the parser missed).
    """
    candidate_json = json.dumps(candidate, indent=2, default=str)
    sections = [
        "Triage this candidate. Return your verdict via the `submit_triage_verdict` tool.",
        "",
        "## Parser output (structured)",
        "```json",
        candidate_json,
        "```",
    ]
    if raw_email_body:
        # Truncate long bodies to keep token use bounded — typical alert
        # bodies are <8KB but HTML-heavy ones can balloon to 40KB+.
        truncated = raw_email_body[:8000]
        sections.extend([
            "",
            "## Raw email body (truncated to 8KB)",
            "```",
            truncated,
            "```",
        ])
    return "\n".join(sections)


# ---------- client ----------

def get_client():
    """Construct and return the Anthropic client. Lazy + cached at the
    module level so tests can patch this without instantiating a real
    client (and without needing ANTHROPIC_API_KEY in the env)."""
    global _client
    if _client is None:
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install -r scripts/requirements.txt"
            ) from e
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Add it to .env at repo root."
            )
        _client = Anthropic(api_key=api_key)
    return _client


_client = None  # module-level singleton


# ---------- triage call ----------

def triage(
    candidate: dict,
    raw_email_body: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    rubric_files: Optional[list] = None,
    system_template_path: Optional[Path] = None,
) -> dict:
    """Send one candidate to Claude and return the parsed verdict dict.

    Verdict dict shape matches the input_schema of submit_triage_verdict
    (see scripts/prompts/triage_tool.json):

        {
          "verdict": "ACTION" | "PASS" | "NEEDS_HUMAN",
          "reasoning": str,
          "key_factors": {...},
          "action_items": [str, ...]    # required when verdict==ACTION
        }

    Optional `rubric_files` and `system_template_path` let a caller
    override the per-vehicle profile without mutating module state —
    useful for an umbrella orchestrator running multiple profiles.

    Raises RuntimeError on auth/config issues or if the API persistently
    fails after MAX_RETRIES. Callers should catch and decide whether to
    re-queue the candidate or mark it NEEDS_HUMAN.
    """
    client = get_client()
    tool_schema = load_triage_tool()

    # System prompt — large + identical across calls (for a given
    # profile), so we mark it for Anthropic's prompt cache. The rubric
    # will be billed at 10% on subsequent calls within the 5-minute
    # cache window. NOTE: switching profiles inside one batch will
    # invalidate the cache between profiles — group by profile if
    # you care about hit rate.
    system_blocks = [
        {
            "type": "text",
            "text": assemble_system_prompt(
                rubric_files=rubric_files,
                system_template_path=system_template_path,
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    user_message = build_user_message(candidate, raw_email_body)

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_blocks,
                tools=[tool_schema],
                tool_choice={"type": "tool", "name": "submit_triage_verdict"},
                messages=[{"role": "user", "content": user_message}],
            )
            verdict = _extract_tool_input(response)
            _log_usage(response, candidate.get("vin"))
            return verdict
        except Exception as e:
            last_exc = e
            if not _is_transient(e) or attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_BASE_DELAY_SEC * (2 ** attempt)
            logger.warning(
                "API call failed (attempt %d/%d): %s. Retrying in %.1fs",
                attempt + 1, MAX_RETRIES, e, delay,
            )
            time.sleep(delay)

    # Should be unreachable, but appease the type checker
    raise RuntimeError(f"Exhausted retries: {last_exc}")


def _extract_tool_input(response) -> dict:
    """Pull the tool_use block's input dict out of the Anthropic response.
    The forced tool_choice means there should be exactly one tool_use
    block; if not, that's a schema violation worth raising."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise RuntimeError(
        f"API response had no tool_use block. content={response.content!r}"
    )


def _log_usage(response, vin: Optional[str]) -> None:
    """Log token usage for cost visibility. Cached input tokens are
    billed at 10%, so the cache hit rate is the main cost lever."""
    try:
        u = response.usage
        logger.info(
            "Triage usage for %s: input=%d (cached=%d, cache_create=%d) output=%d",
            vin or "?",
            getattr(u, "input_tokens", 0),
            getattr(u, "cache_read_input_tokens", 0),
            getattr(u, "cache_creation_input_tokens", 0),
            getattr(u, "output_tokens", 0),
        )
    except Exception:
        pass


def _is_transient(exc: Exception) -> bool:
    """Conservative transient-error check. Anthropic SDK has specific
    exception classes for rate limit and overload, but we duck-type by
    name to avoid coupling to the SDK's internal layout."""
    name = type(exc).__name__
    transient_names = {
        "RateLimitError", "APIConnectionError", "APITimeoutError",
        "InternalServerError", "ServiceUnavailableError",
    }
    return name in transient_names


# ---------- token estimation (used by --dry-run) ----------

def estimate_input_tokens(
    rubric_files: Optional[list] = None,
    system_template_path: Optional[Path] = None,
) -> int:
    """Rough estimate of system-prompt input tokens. Used by --dry-run
    to give a cost sanity check without calling the API.

    Approximation: ~4 chars per token for English text. This will be
    high by 10-20% vs Anthropic's actual tokenizer; for budgeting that
    overestimate is the safe direction.

    Accepts the same per-vehicle profile overrides as
    `assemble_system_prompt`."""
    return len(
        assemble_system_prompt(
            rubric_files=rubric_files,
            system_template_path=system_template_path,
        )
    ) // 4
