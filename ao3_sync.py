#!/usr/bin/env python3
"""Append one public AO3 metadata snapshot to ao3-snapshots.json."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import AO3

OUTPUT = Path(os.getenv("AO3_OUTPUT", "ao3-snapshots.json"))
WORK_URL = os.getenv("AO3_WORK_URL", "").strip()
EXPECTED_TITLE = os.getenv(
    "AO3_EXPECTED_TITLE",
    "The Crew of Dracule Mihawk: A Cross Guild Romance",
).strip()
TIMEZONE = ZoneInfo(os.getenv("AO3_TIMEZONE", "America/New_York"))


def fail(message: str) -> None:
    print(f"AO3 Pulse sync failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_feed() -> dict:
    if not OUTPUT.exists():
        return {
            "schema_version": 1,
            "work": {"work_id": None, "work_url": None, "title": EXPECTED_TITLE},
            "generated_at": None,
            "snapshots": [],
        }
    try:
        payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"could not parse {OUTPUT}: {exc}")
    if isinstance(payload, list):
        payload = {"schema_version": 1, "work": {}, "generated_at": None, "snapshots": payload}
    if not isinstance(payload, dict) or not isinstance(payload.get("snapshots"), list):
        fail("snapshot file has an unsupported shape")
    return payload


def require_nonnegative(name: str, value) -> int:
    if isinstance(value, bool):
        fail(f"{name} was boolean, expected integer")
    try:
        value = int(value)
    except Exception:
        fail(f"{name} was not an integer")
    if value < 0:
        fail(f"{name} was negative")
    return value


def main() -> None:
    if not WORK_URL:
        fail("AO3_WORK_URL is not configured")

    try:
        work_id = AO3.utils.workid_from_url(WORK_URL)
    except Exception as exc:
        fail(f"could not derive a work ID from AO3_WORK_URL: {exc}")

    session = AO3.GuestSession()

    # Avoid a redundant initial request. This makes one fresh metadata request
    # and intentionally skips chapter-text parsing.
    work = AO3.Work(work_id, session=session, load=False)
    try:
        work.reload(False)
    except Exception as exc:
        fail(f"AO3 request failed: {exc}")

    title = str(work.title).strip()
    if EXPECTED_TITLE and title != EXPECTED_TITLE:
        fail(f"title mismatch: expected {EXPECTED_TITLE!r}, received {title!r}")

    now = datetime.now(TIMEZONE).replace(microsecond=0)
    snapshot = {
        "observed_at": now.isoformat(),
        "source": "ao3_api",
        "chapters": require_nonnegative("chapters", work.nchapters),
        "hits": require_nonnegative("hits", work.hits),
        "kudos": require_nonnegative("kudos", work.kudos),
        "comments": require_nonnegative("comments", work.comments),
        "bookmarks": require_nonnegative("bookmarks", work.bookmarks),
        "words": require_nonnegative("words", work.words),
        "ao3_updated_at": work.date_updated.isoformat() if work.date_updated else None,
    }

    if snapshot["chapters"] == 0 or snapshot["words"] == 0:
        fail("AO3 returned implausibly empty metadata; existing history was left untouched")

    feed = load_feed()
    feed.setdefault("schema_version", 1)
    feed["work"] = {
        "work_id": int(work_id),
        "work_url": f"https://archiveofourown.org/works/{int(work_id)}",
        "title": title,
    }
    feed["generated_at"] = now.isoformat()
    feed["snapshots"].append(snapshot)

    seen = set()
    deduped = []

    def sort_key(row: dict) -> str:
        return row.get("observed_at") or row.get("d") or ""

    for row in sorted(feed["snapshots"], key=sort_key):
        if row.get("source") == "historical":
            key = (
                "historical",
                row.get("d"),
                row.get("hits"),
                row.get("kudos"),
                row.get("comments"),
                row.get("bookmarks"),
                row.get("words"),
            )
        else:
            key = ("automated", row.get("observed_at"))
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    feed["snapshots"] = deduped

    temp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temp.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)

    print(
        "AO3 Pulse synced:",
        f"{snapshot['hits']} hits,",
        f"{snapshot['kudos']} kudos,",
        f"{snapshot['comments']} comments,",
        f"{snapshot['bookmarks']} bookmarks,",
        f"{snapshot['chapters']} chapters,",
        f"{snapshot['words']} words",
    )


if __name__ == "__main__":
    main()
