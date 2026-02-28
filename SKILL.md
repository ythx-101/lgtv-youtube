---
name: lgtv-youtube
description: "Remote YouTube control for LG webOS TVs — play/search/pause/skip ads/volume/watch history, without touching the remote. Bypasses the 'select account' interruption. Uses Netflix DIAL screenId leak for auto-pairing. Use when: (1) controlling YouTube on an LG TV, (2) playing music/videos remotely, (3) viewing YouTube watch history, (4) searching/exporting watch history, (5) setting up ad-free YouTube via Developer Mode."
---

# LG TV YouTube Remote Control

## Overview

Control YouTube on LG webOS TVs entirely remotely. Core innovation: **Netflix DIAL screenId leak** to obtain YouTube Lounge tokens — no manual pairing needed.

## Prerequisites

- LG webOS TV (tested on webOS 22 / OLED C2, should work on webOS 6+)
- TV and control machine on the same network (or SSH tunnel)
- Python 3.8+ with `pyytlounge` (`pip install pyytlounge`)

## Quick Start

```bash
# 1. Get your TV's screenId (one-time, from same network as TV)
python3 scripts/get_lounge_token.py --tv-ip <TV_IP>

# 2. Play a video
python3 scripts/tv_youtube.py play <VIDEO_ID>

# 3. Search and play
python3 scripts/tv_youtube.py search "邓紫棋 光年之外"
```

## Commands

| Command | Description |
|---------|-------------|
| `play <video_id>` | Play a specific YouTube video |
| `search "query"` | Search YouTube and play first result |
| `playlist "q1,q2,q3"` | Queue multiple videos (IDs or search queries, comma-separated) |
| `next` | Next track |
| `prev` | Previous track |
| `pause` | Pause playback |
| `resume` | Resume playback |
| `skip` | Skip current ad |
| `volume <0-100>` | Set volume |
| `now` | Show now playing info |
| `renew` | Renew Lounge token |

## How It Works

### The Problem

LG webOS YouTube app interrupts playback every ~30 seconds with an "account selection" screen. YouTube's official Lounge pairing API (`/api/lounge/pairing/get_screen`) was globally shut down — no way to get tokens remotely.

### The Solution: Netflix DIAL Leak

LG TVs expose a DIAL (Discovery and Launch) service on port 36866. While YouTube's DIAL endpoint returns 403, **Netflix's DIAL endpoint returns 200** and leaks the TV's `screenId` in its XML response.

This screenId can be used directly with YouTube's `get_lounge_token_batch` endpoint (which is still alive) to obtain a Lounge token valid for **14 days** with auto-renewal.

Flow:
```
GET http://<TV_IP>:36866/apps/Netflix
  → XML response contains <screenId>xxx</screenId>
POST https://www.youtube.com/api/lounge/pairing/get_lounge_token_batch
  body: screen_ids=xxx
  → JSON with loungeToken (14-day validity)
```

### Token Lifecycle

- Token valid for ~14 days
- `scripts/tv_youtube.py` auto-renews on expiry
- screenId is persistent (doesn't change across reboots)

## Optional: Ad-Free YouTube (Developer Mode)

For ad-free YouTube via youtube-webos, see [references/developer-mode.md](references/developer-mode.md).

## Watch History

View, search, and export your YouTube watch history. Requires YouTube cookies (one-time setup).

### Cookie Setup

1. Install **EditThisCookie V3** Chrome extension
2. Open `youtube.com` (make sure you're logged in)
3. Click the EditThisCookie icon → click the export button (5th from left)
4. Send the exported text to your agent

```bash
# Import cookies (EditThisCookie JSON auto-converts to Netscape)
python3 scripts/yt_history.py import cookies.json

# Import from stdin (agent pipes text directly)
echo '<cookie text>' | python3 scripts/yt_history.py import -

# Check if cookies are valid
python3 scripts/yt_history.py check
```

Cookies are stored at `data/youtube-cookies.txt`. They stay there until you delete them.

### History Commands

```bash
python3 scripts/yt_history.py show            # Recent 20 videos
python3 scripts/yt_history.py show 50          # Recent 50 videos
python3 scripts/yt_history.py search "keyword" # Search history
python3 scripts/yt_history.py export json      # Export to JSON
python3 scripts/yt_history.py export csv       # Export to CSV
python3 scripts/yt_history.py show --no-cache  # Force refresh (skip 5-min cache)
```

## Troubleshooting

- **"Not linked" error**: Token expired. Run `python3 scripts/tv_youtube.py renew`
- **No sound**: TV screen may be off (energy saver). Video still plays — send any SSAP command to wake
- **DIAL port 36866 not responding**: TV may be in deep sleep. Wake via Wake-on-LAN or SSAP first
- **"Cookies expired"**: Re-export from EditThisCookie and re-import
