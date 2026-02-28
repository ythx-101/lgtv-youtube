# lgtv-youtube

Remote YouTube control for LG webOS TVs — play, search, pause, skip ads, adjust volume. No remote needed.

**Core innovation**: Uses a Netflix DIAL screenId leak to obtain YouTube Lounge tokens automatically — no manual TV-side pairing required.

An [OpenClaw](https://github.com/openclaw/openclaw) skill. Python 3.8+. Single dependency: `pyytlounge`.

> **For AI Agents**: All commands are scriptable. Import `get_lounge_token.py` as a Python module for direct integration.

## The Problem

LG webOS YouTube app interrupts playback with an "account selection" screen. YouTube's official Lounge pairing API (`/api/lounge/pairing/get_screen`) was shut down globally — no way to get tokens remotely.

## The Solution

LG TVs expose a DIAL service on port 36866. YouTube's DIAL endpoint returns 403, but **Netflix's DIAL endpoint returns 200** and leaks the TV's `screenId` in its XML response.

This screenId works with YouTube's `get_lounge_token_batch` endpoint to obtain a Lounge token valid for **14 days** with auto-renewal.

```
GET http://<TV_IP>:36866/apps/Netflix
  → XML with <screenId>xxx</screenId>

POST https://www.youtube.com/api/lounge/pairing/get_lounge_token_batch
  body: screen_ids=xxx
  → loungeToken (14-day validity)
```

## Quick Start

```bash
pip install pyytlounge

# 1. Get token (one-time, from same network as TV)
python3 scripts/get_lounge_token.py --tv-ip 192.168.1.100

# 2. Play a video
python3 scripts/tv_youtube.py play dQw4w9WgXcQ

# 3. Search and play
python3 scripts/tv_youtube.py search "Adele Hello"
```

## Commands

| Command | Description |
|---------|-------------|
| `play <video_id>` | Play a specific YouTube video |
| `search "query"` | Search YouTube and play first result |
| `playlist "q1,q2,q3"` | Queue multiple videos (IDs or search queries) |
| `next` | Next track |
| `prev` | Previous track |
| `pause` | Pause playback |
| `resume` | Resume playback |
| `skip` | Skip current ad |
| `volume <0-100>` | Set TV volume |
| `now` | Show now playing info |
| `renew` | Renew Lounge token |

## For Python

```python
from scripts.get_lounge_token import get_screen_id, get_lounge_token

# Get screenId from Netflix DIAL (same network as TV)
screen_id = get_screen_id("192.168.1.100")

# Exchange for Lounge token
auth = get_lounge_token(screen_id)
# Returns: {"screenId": "...", "loungeToken": "...", "expiration": ...}
```

## How It Works

```
┌─────────┐    DIAL port 36866     ┌──────────┐
│  Script  │ ───GET /apps/Netflix──▶│  LG TV   │
│          │ ◀──XML (screenId)───── │          │
└────┬─────┘                        └──────────┘
     │
     │  POST get_lounge_token_batch
     ▼
┌──────────────┐                    ┌──────────┐
│  YouTube API │ ──loungeToken────▶ │ TV YouTube│
│              │    (14 days)       │   App     │
└──────────────┘                    └──────────┘
```

1. **Netflix DIAL leak**: `GET /apps/Netflix` on TV port 36866 returns XML containing `<screenId>`
2. **Token exchange**: POST screenId to YouTube's `get_lounge_token_batch` → get loungeToken
3. **Remote control**: Use loungeToken with [pyytlounge](https://github.com/nicx/pyytlounge) to control playback

The screenId is persistent across reboots. Token auto-renews on expiry.

## Optional: Ad-Free YouTube

Install [youtube-webos](https://github.com/nicx/youtube-webos) for ad-free YouTube via Developer Mode. See [docs/developer-mode.md](docs/developer-mode.md).

## Tested On

- LG OLED C2 (webOS 22)
- Should work on webOS 6+ (any LG TV with Netflix + DIAL)

## Requirements

- Python 3.8+
- `pyytlounge` (`pip install pyytlounge`)
- TV and script on the same network (or SSH tunnel)
- Netflix app installed on TV (for DIAL screenId)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Not linked" error | Token expired. Run `tv_youtube.py renew` |
| No sound | TV screen may be off (energy saver). Send any SSAP command to wake |
| DIAL port 36866 not responding | TV in deep sleep. Wake via WoL or SSAP first |
| `ModuleNotFoundError: pyytlounge` | `pip install pyytlounge` |

## License

MIT
