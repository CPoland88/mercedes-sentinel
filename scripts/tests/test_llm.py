"""Tests for scripts/llm.py — specifically the per-vehicle profile
override hooks added so the same infrastructure can serve multiple
vehicle pursuits.

These are tiny by design: they prove the override path works without
exercising the live Anthropic client.

REPO_ROOT is monkeypatched into a per-test tempdir, so fake rubric
files live in disposable scratch space rather than alongside the real
project files.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import llm


# The Mercedes rubric (CONTEXT.md + 4 references) adds many KB on top
# of the system template. An override that swaps the rubric for a tiny
# stub file should produce a prompt at least this much shorter than
# the default — proves the rubric was actually replaced rather than
# additively appended.
_RUBRIC_SAVINGS_FLOOR = 5000  # chars


class TestAssembleSystemPromptDefaults(unittest.TestCase):
    """Baseline: defaults preserve current Mercedes Sentinel behavior."""

    def test_default_prompt_includes_template_and_rubric(self):
        prompt = llm.assemble_system_prompt()
        # System template marker — the verdict definitions block.
        self.assertIn("ACTION", prompt)
        self.assertIn("PASS", prompt)
        self.assertIn("NEEDS_HUMAN", prompt)
        # CONTEXT.md / references content marker — the buyer's anchor
        # location appears multiple times across the real rubric.
        self.assertIn("Vienna", prompt)


class TestAssembleSystemPromptOverrides(unittest.TestCase):
    """Override path: a different rubric file list and/or template
    yields a different prompt, without mutating module state."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        # A fake rubric file under the fake REPO_ROOT
        (self.tmpdir / "fake_rubric.md").write_text(
            "# Fake Rubric\nThis is a Corvette-flavored marker.\n",
            encoding="utf-8",
        )
        # A fake system template — path-overridden so it can live
        # outside the fake REPO_ROOT
        self.fake_template = self.tmpdir / "fake_system.md"
        self.fake_template.write_text(
            "# Fake System\nThis is a different prompt header.\n",
            encoding="utf-8",
        )

    def test_custom_rubric_files_replaces_defaults(self):
        default_prompt = llm.assemble_system_prompt()
        with patch.object(llm, "REPO_ROOT", self.tmpdir):
            override_prompt = llm.assemble_system_prompt(
                rubric_files=["fake_rubric.md"],
            )
        # Custom rubric content present
        self.assertIn("Corvette-flavored marker", override_prompt)
        # The default *template* is still used (we only overrode the
        # rubric list), so the verdict definitions still appear.
        self.assertIn("ACTION", override_prompt)
        # The override prompt should be meaningfully shorter than the
        # default — proves the real rubric was actually replaced rather
        # than appended to.
        savings = len(default_prompt) - len(override_prompt)
        self.assertGreater(savings, _RUBRIC_SAVINGS_FLOOR)

    def test_custom_system_template_replaces_default(self):
        with patch.object(llm, "REPO_ROOT", self.tmpdir):
            prompt = llm.assemble_system_prompt(
                rubric_files=[],
                system_template_path=self.fake_template,
            )
        # Custom template content present
        self.assertIn("This is a different prompt header.", prompt)
        # Default template's Mercedes-specific verbiage NOT present
        self.assertNotIn("Mercedes-Benz GLS", prompt)
        # Empty rubric + tiny template → very small prompt
        self.assertLess(len(prompt), 200)

    def test_overrides_do_not_mutate_module_state(self):
        snapshot_files = list(llm.RUBRIC_FILES)
        snapshot_template = llm.SYSTEM_TEMPLATE_PATH
        snapshot_repo_root = llm.REPO_ROOT
        with patch.object(llm, "REPO_ROOT", self.tmpdir):
            _ = llm.assemble_system_prompt(
                rubric_files=["fake_rubric.md"],
                system_template_path=self.fake_template,
            )
        self.assertEqual(list(llm.RUBRIC_FILES), snapshot_files)
        self.assertEqual(llm.SYSTEM_TEMPLATE_PATH, snapshot_template)
        self.assertEqual(llm.REPO_ROOT, snapshot_repo_root)
        # And a subsequent default call still produces the Mercedes prompt
        default_prompt = llm.assemble_system_prompt()
        self.assertIn("Vienna", default_prompt)


class TestEstimateInputTokensOverrides(unittest.TestCase):
    """estimate_input_tokens should honor the same overrides — the
    --dry-run path needs to be able to size a different profile."""

    def test_estimate_scales_with_rubric_size(self):
        default_tokens = llm.estimate_input_tokens()
        empty_tokens = llm.estimate_input_tokens(rubric_files=[])
        # Removing the rubric should produce a smaller estimate
        self.assertGreater(default_tokens, empty_tokens)


if __name__ == "__main__":
    unittest.main()
