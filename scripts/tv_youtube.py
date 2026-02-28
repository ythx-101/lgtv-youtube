#!/usr/bin/env python3
"""
YouTube remote control for LG webOS TVs via pyytlounge.
Auto-renews Lounge token on expiry using Netflix DIAL bypass.

Usage:
    python3 tv_youtube.py play <video_id> [--auth auth.json]
    python3 tv_youtube.py search "query" [--auth auth.json]
    python3 tv_youtube.py pause
    python3 tv_youtube.py resume
    python3 tv_youtube.py skip
    python3 tv_youtube.py volume 30
    python3 tv_youtube.py renew --tv-ip 192.168.1.100

Requires: pip install pyytlounge
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.request

# Ensure sibling scripts are importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
DEFAULT_AUTH = os.path.join(SCRIPT_DIR, "..", "ytlounge-auth.json")


def load_auth(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_auth(path: str, auth: dict):
    with open(path, "w") as f:
        json.dump(auth, f, indent=2)


def renew_token(tv_ip: str = None, auth_path: str = None) -> dict:
    """Renew token. Uses saved screenId if tv_ip not provided."""
    from get_lounge_token import get_lounge_token, get_screen_id

    if tv_ip:
        screen_id = get_screen_id(tv_ip)
    elif auth_path and os.path.exists(auth_path):
        screen_id = load_auth(auth_path).get("screenId")
    else:
        raise RuntimeError("Need --tv-ip or existing auth file with screenId")

    auth = get_lounge_token(screen_id)
    if auth_path:
        save_auth(auth_path, auth)
    return auth


def search_youtube(query: str) -> tuple:
    """Search YouTube, return (video_id, title) of first result."""
    q = urllib.request.quote(query)
    req = urllib.request.Request(
        f"https://www.youtube.com/results?search_query={q}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    html = urllib.request.urlopen(req, timeout=10).read().decode()
    ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
    seen = set()
    unique = [x for x in ids if not (x in seen or seen.add(x))]
    if not unique:
        return None, None
    vid = unique[0]
    # Get title
    try:
        info = json.loads(
            urllib.request.urlopen(
                f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={vid}",
                timeout=5,
            ).read().decode()
        )
        title = info.get("title", vid)
    except Exception:
        title = vid
    return vid, title


async def run(args):
    from pyytlounge import YtLoungeApi

    auth_path = args.auth
    auth = load_auth(auth_path)

    async with YtLoungeApi("LGTVRemote") as api:
        api.auth.screen_id = auth["screenId"]
        api.auth.lounge_id_token = auth["loungeToken"]
        api.auth.expiry = auth.get("expiration", 0)

        try:
            await api.connect()
        except Exception as e:
            if "linked" in str(e).lower():
                print("Token expired, renewing...")
                auth = renew_token(
                    tv_ip=getattr(args, "tv_ip", None), auth_path=auth_path
                )
                api.auth.lounge_id_token = auth["loungeToken"]
                api.auth.expiry = auth.get("expiration", 0)
                await api.connect()
            else:
                raise

        cmd = args.command

        if cmd == "play":
            await api.play_video(args.target)
            print(f"▶ Playing: {args.target}")

        elif cmd == "search":
            query = args.target
            print(f"🔍 Searching: {query}")
            vid, title = search_youtube(query)
            if vid:
                await api.play_video(vid)
                print(f"▶ Playing: {title}")
            else:
                print("❌ No results")
                return

        elif cmd == "pause":
            await api.pause()
            print("⏸ Paused")

        elif cmd == "resume":
            await api.play()
            print("▶ Resumed")

        elif cmd == "skip":
            await api.skip_ad()
            print("⏭ Ad skipped")

        elif cmd == "volume":
            await api.set_volume(int(args.target))
            print(f"🔊 Volume: {args.target}")

        elif cmd == "renew":
            auth = renew_token(tv_ip=args.tv_ip, auth_path=auth_path)
            days = (auth["expiration"] / 1000 - time.time()) / 86400
            print(f"✅ Token renewed ({days:.1f} days)")
            return

        await asyncio.sleep(2)


def main():
    parser = argparse.ArgumentParser(description="LG TV YouTube Remote")
    parser.add_argument("command", choices=["play", "search", "pause", "resume", "skip", "volume", "renew"])
    parser.add_argument("target", nargs="?", help="Video ID, search query, or volume level")
    parser.add_argument("--auth", default=DEFAULT_AUTH, help="Auth JSON file path")
    parser.add_argument("--tv-ip", help="TV IP (for renew command)")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
