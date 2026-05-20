"""Gmail IMAP poll for the MB-Sentinel label.

Connects via IMAP over TLS using an app password loaded from `.env`
(`IMAP_USERNAME`, `IMAP_APP_PASSWORD`). Gmail labels appear as IMAP
folders; the default label name is `MB-Sentinel` matching the watchlist
setup in the project docs.

Usage:

    with mail.from_env() as poller:
        for uid, raw_bytes in poller.fetch_unread():
            ...
            poller.mark_read(uid)
"""
from __future__ import annotations

import imaplib
import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
DEFAULT_LABEL = "MB-Sentinel"


class MailPoller:
    def __init__(self, username: str, app_password: str, label: str = DEFAULT_LABEL):
        self.username = username
        self.app_password = app_password
        self.label = label
        self._conn: imaplib.IMAP4_SSL | None = None

    def __enter__(self) -> "MailPoller":
        self._conn = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST, GMAIL_IMAP_PORT)
        self._conn.login(self.username, self.app_password)
        # Quote the label name to be safe (Gmail labels can contain spaces).
        status, _ = self._conn.select(f'"{self.label}"')
        if status != "OK":
            raise RuntimeError(
                f"Could not select Gmail label {self.label!r} (status={status}). "
                "Verify the label exists and your filter is routing alerts to it."
            )
        return self

    def __exit__(self, *args) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        except Exception:
            pass
        try:
            self._conn.logout()
        except Exception:
            pass

    def fetch_unread(self) -> List[Tuple[bytes, bytes]]:
        """Return list of (uid_bytes, raw_email_bytes) for UNSEEN messages."""
        if self._conn is None:
            raise RuntimeError("MailPoller not entered as a context manager")

        status, data = self._conn.uid("SEARCH", None, "UNSEEN")
        if status != "OK":
            raise RuntimeError(f"IMAP SEARCH UNSEEN failed (status={status})")
        uids = data[0].split() if data and data[0] else []
        results: List[Tuple[bytes, bytes]] = []
        for uid in uids:
            status, msg_data = self._conn.uid("FETCH", uid, "(RFC822)")
            if status != "OK":
                logger.warning("Failed to fetch uid=%s (status=%s)", uid, status)
                continue
            # msg_data structure: [(b'... (RFC822 {N}', b'<raw>'), b')']
            raw = None
            for part in msg_data:
                if isinstance(part, tuple) and len(part) >= 2:
                    raw = part[1]
                    break
            if raw is None:
                logger.warning("No payload in fetch for uid=%s", uid)
                continue
            results.append((uid, raw))
        return results

    def mark_read(self, uid: bytes) -> None:
        if self._conn is None:
            raise RuntimeError("MailPoller not entered as a context manager")
        self._conn.uid("STORE", uid, "+FLAGS", "\\Seen")


def from_env() -> MailPoller:
    """Construct a MailPoller from `IMAP_USERNAME` and `IMAP_APP_PASSWORD`
    environment variables (loaded via python-dotenv at process start)."""
    username = os.environ.get("IMAP_USERNAME")
    password = os.environ.get("IMAP_APP_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "Missing IMAP credentials. Set IMAP_USERNAME and IMAP_APP_PASSWORD "
            "in .env at repo root."
        )
    return MailPoller(username, password)
