#!/usr/bin/env python3
"""
YouTube watch history — view, search, export.

Setup:
  1. Install EditThisCookie V3 in Chrome
  2. Open youtube.com (logged in)
  3. Export cookies → send to your agent

Usage:
  python3 yt_history.py import cookies.json       # Import EditThisCookie JSON
  python3 yt_history.py import cookies.txt         # Import Netscape cookies.txt
  python3 yt_history.py import -                   # Import from stdin
  python3 yt_history.py show                       # Recent 20
  python3 yt_history.py show 50                    # Recent 50
  python3 yt_history.py search "keyword"           # Search history
  python3 yt_history.py export json                # Export JSON
  python3 yt_history.py export csv                 # Export CSV
  python3 yt_history.py check                      # Validate cookies

Requires: yt-dlp (pip install yt-dlp)
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COOKIES_FILE = DATA_DIR / "youtube-cookies.txt"
CACHE_FILE = DATA_DIR / "history-cache.json"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _editthiscookie_to_netscape(etc_json: list) -> str:
    """Convert EditThisCookie V3 JSON to Netscape cookies.txt format."""
    lines = ["# Netscape HTTP Cookie File", ""]
    for c in etc_json:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = str(int(c.get("expirationDate", 0)))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
    return "\n".join(lines) + "\n"


def cmd_import(args):
    """Import cookies from file or stdin."""
    ensure_data_dir()

    if args.source == "-":
        content = sys.stdin.read().strip()
    else:
        p = Path(args.source)
        if not p.exists():
            print(f"❌ File not found: {args.source}")
            sys.exit(1)
        content = p.read_text(encoding="utf-8").strip()

    # Detect format
    if content.startswith("[") or content.startswith("{"):
        data = json.loads(content)
        if isinstance(data, dict):
            data = [data]
        netscape = _editthiscookie_to_netscape(data)
        COOKIES_FILE.write_text(netscape, encoding="utf-8")
        print(f"✅ Imported {len(data)} cookies (EditThisCookie → Netscape)")
    else:
        COOKIES_FILE.write_text(content, encoding="utf-8")
        count = len([l for l in content.split("\n") if l.strip() and not l.startswith("#")])
        print(f"✅ Imported {count} cookies (Netscape format)")

    print(f"📁 Stored at: {COOKIES_FILE}")


def cmd_check(args):
    """Check if cookies are valid."""
    if not COOKIES_FILE.exists():
        print("❌ No cookies file found. Run: yt_history.py import <file>")
        return

    try:
        r = subprocess.run(
            ["yt-dlp", "--cookies", str(COOKIES_FILE), "--flat-playlist",
             ":ythistory", "--print", "%(id)s", "--playlist-items", "1",
             "--no-download", "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0 and r.stdout.strip():
            print("✅ Cookies valid — YouTube history accessible")
        else:
            print("❌ Cookies expired or invalid — please re-import")
    except FileNotFoundError:
        print("❌ yt-dlp not found. Install: pip install yt-dlp")


def _fetch(limit: int = 20, no_cache: bool = False) -> list:
    """Fetch YouTube watch history via yt-dlp."""
    if not COOKIES_FILE.exists():
        print("❌ No cookies. Run: yt_history.py import <file>")
        sys.exit(1)

    # Cache (5 min)
    if not no_cache and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text())
            if time.time() - cache.get("ts", 0) < 300:
                entries = cache.get("entries", [])
                if len(entries) >= limit:
                    return entries[:limit]
        except Exception:
            pass

    print(f"🔄 Fetching last {limit} videos...")

    try:
        r = subprocess.run(
            ["yt-dlp", "--cookies", str(COOKIES_FILE), "--flat-playlist",
             ":ythistory",
             "--print", "%(id)s\t%(title)s\t%(channel)s\t%(duration_string)s\t%(upload_date)s",
             f"--playlist-items", f"1:{limit}",
             "--no-download", "--no-warnings"],
            capture_output=True, text=True, timeout=60
        )
    except FileNotFoundError:
        print("❌ yt-dlp not found. Install: pip install yt-dlp")
        sys.exit(1)

    if r.returncode != 0:
        stderr = r.stderr.strip()
        if "Login" in stderr or "cookie" in stderr.lower():
            print("❌ Cookies expired — please re-import")
        else:
            print(f"❌ Failed: {stderr[:300]}")
        sys.exit(1)

    entries = []
    for line in r.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        vid = parts[0] if len(parts) > 0 else ""
        entries.append({
            "id": vid,
            "title": parts[1] if len(parts) > 1 else vid,
            "channel": parts[2] if len(parts) > 2 else "",
            "duration": parts[3] if len(parts) > 3 else "",
            "upload_date": parts[4] if len(parts) > 4 else "",
            "url": f"https://www.youtube.com/watch?v={vid}",
        })

    # Save cache
    ensure_data_dir()
    try:
        CACHE_FILE.write_text(json.dumps({"ts": time.time(), "entries": entries}, ensure_ascii=False, indent=2))
    except Exception:
        pass

    return entries


def cmd_show(args):
    """Show recent watch history."""
    limit = args.count or 20
    entries = _fetch(limit, no_cache=args.no_cache)
    if not entries:
        print("📭 No history found")
        return

    print(f"\n📺 YouTube Watch History ({len(entries)} videos)\n")
    for i, e in enumerate(entries, 1):
        meta = []
        if e["channel"]:
            meta.append(e["channel"])
        if e["duration"]:
            meta.append(e["duration"])
        info = f"  [{' · '.join(meta)}]" if meta else ""
        print(f"  {i:>3}. {e['title']}{info}")
        print(f"       https://youtube.com/watch?v={e['id']}")
    print()


def cmd_search(args):
    """Search watch history."""
    entries = _fetch(limit=200, no_cache=args.no_cache)
    kw = args.keyword.lower()
    results = [e for e in entries if kw in e["title"].lower() or kw in e["channel"].lower()]

    if results:
        print(f"\n🔍 \"{args.keyword}\" — {len(results)} matches\n")
        for i, e in enumerate(results, 1):
            meta = []
            if e["channel"]:
                meta.append(e["channel"])
            if e["duration"]:
                meta.append(e["duration"])
            info = f"  [{' · '.join(meta)}]" if meta else ""
            print(f"  {i:>3}. {e['title']}{info}")
            print(f"       https://youtube.com/watch?v={e['id']}")
        print()
    else:
        print(f"\n🔍 \"{args.keyword}\" — no matches in last 200 videos")


def cmd_export(args):
    """Export history to file."""
    entries = _fetch(limit=args.count or 100, no_cache=args.no_cache)
    if not entries:
        print("📭 Nothing to export")
        return

    ensure_data_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.format == "json":
        out = DATA_DIR / f"history-{ts}.json"
        out.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        out = DATA_DIR / f"history-{ts}.csv"
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["id", "title", "channel", "duration", "upload_date", "url"])
        w.writeheader()
        w.writerows(entries)
        out.write_text(buf.getvalue(), encoding="utf-8")

    print(f"✅ Exported {len(entries)} videos → {out}")


def main():
    parser = argparse.ArgumentParser(description="YouTube Watch History")
    sub = parser.add_subparsers(dest="cmd")

    p_import = sub.add_parser("import", help="Import cookies")
    p_import.add_argument("source", help="Cookie file path, or '-' for stdin")

    sub.add_parser("check", help="Validate cookies")

    p_show = sub.add_parser("show", help="Show recent history")
    p_show.add_argument("count", nargs="?", type=int, default=20, help="Number of videos (default: 20)")
    p_show.add_argument("--no-cache", action="store_true")

    p_search = sub.add_parser("search", help="Search history")
    p_search.add_argument("keyword", help="Search keyword")
    p_search.add_argument("--no-cache", action="store_true")

    p_export = sub.add_parser("export", help="Export history")
    p_export.add_argument("format", choices=["json", "csv"])
    p_export.add_argument("--count", type=int, default=100)
    p_export.add_argument("--no-cache", action="store_true")

    args = parser.parse_args()

    cmds = {"import": cmd_import, "check": cmd_check, "show": cmd_show,
            "search": cmd_search, "export": cmd_export}
    if args.cmd in cmds:
        cmds[args.cmd](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
