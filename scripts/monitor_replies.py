#!/usr/bin/env python3
"""
X Monitor - Monitor tweet replies via Camofox + Nitter.
No login required. Read-only.
"""

import json
import re
import sys
import os
import argparse
import urllib.request
import time
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path


STATE_FILE = Path(__file__).parent.parent / "data" / "state.json"


def parse_tweet_url(url: str) -> tuple:
    match = re.search(r"(?:x\.com|twitter\.com)/(\w+)/status/(\d+)", url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError(f"Cannot parse tweet URL: {url}")


def load_state() -> Dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: Dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def fetch_replies_via_camofox(
    username: str,
    tweet_id: str,
    camofox_port: int = 9377,
    nitter_instance: str = "nitter.net",
) -> Optional[List[Dict]]:
    nitter_url = f"https://{nitter_instance}/{username}/status/{tweet_id}"

    try:
        create_data = json.dumps({
            "userId": "x-monitor",
            "sessionKey": f"monitor-{tweet_id}",
            "url": nitter_url,
        }).encode()

        req = urllib.request.Request(
            f"http://localhost:{camofox_port}/tabs",
            data=create_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            tab_data = json.loads(resp.read().decode())

        tab_id = tab_data.get("tabId")
        if not tab_id:
            print("[Camofox] No tabId returned", file=sys.stderr)
            return None

        time.sleep(8)

        snap_url = f"http://localhost:{camofox_port}/tabs/{tab_id}/snapshot?userId=x-monitor"
        req = urllib.request.Request(snap_url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            snap_data = json.loads(resp.read().decode())

        snapshot = snap_data.get("snapshot", "")

        try:
            close_req = urllib.request.Request(
                f"http://localhost:{camofox_port}/tabs/{tab_id}",
                method="DELETE",
            )
            urllib.request.urlopen(close_req, timeout=5)
        except Exception:
            pass

        replies = parse_replies(snapshot, username)
        return replies

    except Exception as e:
        print(f"[Camofox] Error: {e}", file=sys.stderr)
        return None


def parse_replies(snapshot: str, original_author: str) -> List[Dict]:
    """Parse reply data from Camofox/Nitter snapshot.

    Real snapshot format for a reply block:
        - link [eN]:           <- reply permalink
        - link "DisplayName":  <- author display name
        - link "@handle":      <- author handle
        - link "12h":          <- time ago
        - text: Replying to    <- reply marker
        - link "@original":    <- who they replied to
        - text: actual reply content  1   2  185  <- text + stats
    """
    replies = []
    lines = snapshot.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line == "- text: Replying to":
            author_handle = None
            author_name = None
            reply_text = None
            time_ago = None
            likes = 0
            replies_count = 0
            views = 0

            # Look backwards for author info
            for j in range(i - 1, max(0, i - 15), -1):
                prev = lines[j].strip()
                # Match @handle (not the original author)
                if not author_handle:
                    m = re.search(r'link\s+"@(\w+)"', prev)
                    if m and m.group(1).lower() != original_author.lower():
                        author_handle = f"@{m.group(1)}"
                # Match display name (not a time like "12h", not nav items)
                if not author_name:
                    m = re.search(r'link\s+"([^@][^"]*)"', prev)
                    if m:
                        name = m.group(1)
                        skip = re.match(r'^\d+[hmd]$', name) or name in (
                            "nitter", "Logo", "more replies",
                        )
                        if not skip:
                            author_name = name
                # Match time ago
                if not time_ago:
                    m = re.search(r'link\s+"(\d+[hmd])"', prev)
                    if m:
                        time_ago = m.group(1)

                if author_handle and author_name and time_ago:
                    break

            # Look forward: skip "link @..." line, then get reply text
            for j in range(i + 1, min(len(lines), i + 5)):
                fwd = lines[j].strip()
                if re.search(r'link\s+"@\w+"', fwd):
                    continue
                if fwd.startswith("- text:"):
                    raw = fwd[len("- text:"):].strip()
                    # Nitter uses private-use Unicode icons for stats:
                    # U+E803=replies U+E80C=retweets U+E801=likes U+E800=views
                    _ICO = "\ue803|\ue80c|\ue801|\ue800"
                    stat_match = re.search(
                        "^(.*?)\\s+\ue803\\s*(\\d+)\\s*\ue80c\\s*\ue801\\s*(\\d+)\\s*\ue800\\s*(\\d+)",
                        raw,
                    )
                    if stat_match:
                        reply_text = stat_match.group(1).strip()
                        replies_count = int(stat_match.group(2))
                        likes = int(stat_match.group(3))
                        views = int(stat_match.group(4))
                    else:
                        # Fallback: strip any trailing icon+number sequences
                        cleaned = re.sub(
                            "\\s*[\ue800-\ue8ff]\\s*[\\d,]+", "", raw
                        ).strip()
                        reply_text = cleaned if cleaned else raw
                    break

            if author_handle and reply_text:
                reply = {
                    "author": author_handle,
                    "author_name": author_name or author_handle,
                    "text": reply_text,
                    "time_ago": time_ago,
                    "likes": likes,
                    "replies": replies_count,
                    "views": views,
                    "is_question": is_question(reply_text),
                }
                if not any(
                    r["author"] == author_handle and r["text"] == reply_text
                    for r in replies
                ):
                    replies.append(reply)

        i += 1

    return replies


def is_question(text: str) -> bool:
    markers = [
        "?", "\uff1f",
        "\u600e\u4e48", "\u5982\u4f55", "\u4e3a\u4ec0\u4e48", "\u4e3a\u5565",
        "\u4ec0\u4e48\u539f\u56e0", "\u8bf7\u6559", "\u8bf7\u95ee",
        "\u80fd\u4e0d\u80fd", "\u53ef\u4ee5\u5417", "\u662f\u4ec0\u4e48",
        "\u600e\u6837", "\u4f1a\u4e0d\u4f1a", "\u5417", "\u5462",
        "\u591a\u5c11", "\u54ea\u4e2a",
        "how", "why", "what", "can you", "is there", "does", "could",
    ]
    text_lower = text.lower()
    return any(marker in text_lower for marker in markers)


def monitor_tweet(
    url: str,
    watch: bool = False,
    camofox_port: int = 9377,
    nitter_instance: str = "nitter.net",
) -> Dict[str, Any]:
    username, tweet_id = parse_tweet_url(url)

    result = {
        "tweet_url": url,
        "username": username,
        "tweet_id": tweet_id,
        "checked_at": datetime.utcnow().isoformat(),
    }

    replies = fetch_replies_via_camofox(
        username, tweet_id, camofox_port, nitter_instance
    )

    if replies is None:
        result["error"] = "Failed to fetch replies (is Camofox running?)"
        return result

    result["total_replies"] = len(replies)
    result["questions"] = [r for r in replies if r.get("is_question")]
    result["question_count"] = len(result["questions"])

    if watch:
        state = load_state()
        prev_key = f"tweet_{tweet_id}"
        prev_authors = set()
        if prev_key in state:
            prev_authors = set(
                "{}:{}".format(r["author"], r["text"])
                for r in state[prev_key].get("replies", [])
            )

        new_replies = [
            r for r in replies
            if "{}:{}".format(r["author"], r["text"]) not in prev_authors
        ]
        result["new_replies"] = new_replies
        result["new_count"] = len(new_replies)

        state[prev_key] = {
            "replies": replies,
            "last_checked": result["checked_at"],
        }
        save_state(state)
    else:
        result["replies"] = replies

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monitor X/Twitter tweet replies via Camofox + Nitter"
    )
    parser.add_argument("--url", "-u", required=True, help="Tweet URL")
    parser.add_argument(
        "--watch", "-w", action="store_true",
        help="Watch mode: show only new replies since last check",
    )
    parser.add_argument("--pretty", "-p", action="store_true")
    parser.add_argument("--port", type=int, default=9377)
    parser.add_argument("--nitter", default="nitter.net")

    args = parser.parse_args()
    result = monitor_tweet(
        args.url,
        watch=args.watch,
        camofox_port=args.port,
        nitter_instance=args.nitter,
    )

    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
