# Developer Mode & youtube-webos Installation

## Overview

Install youtube-webos (ad-free YouTube) on LG webOS TVs via Developer Mode SSH.

## Prerequisites

- LG Developer account: https://webostv.developer.lge.com
- Developer Mode app installed from LG Content Store
- `@webos-tools/cli`: `npm install -g @webos-tools/cli`

## Steps

### 1. Enable Developer Mode

- Open Developer Mode app on TV
- Log in with LG Developer credentials
- Toggle "Dev Mode Status" → ON (TV reboots)
- Toggle "Key Server" → ON
- Note the Passphrase (6 characters, bottom-left)

### 2. Setup ares-cli

```bash
ares-setup-device -a lgtv -i "username=prisoner,host=<TV_IP>,port=9922"
```

### 3. Get SSH Key

```bash
ares-novacom --device lgtv --getkey
# Enter the Passphrase from Developer Mode app
```

**Known issue**: If ares fails with "All configured authentication methods failed",
the TV uses ssh-rsa which newer ssh2 libraries reject. Fix:

```bash
# Get key manually via HTTP
curl -s http://<TV_IP>:9991/webos_rsa > ~/.ssh/lgtv_webos

# Decrypt with passphrase
openssl rsa -in ~/.ssh/lgtv_webos -out ~/.ssh/lgtv_webos -traditional -passin pass:<PASSPHRASE>
chmod 600 ~/.ssh/lgtv_webos

# SSH directly
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -i ~/.ssh/lgtv_webos -p 9922 prisoner@<TV_IP>
```

### 4. Install youtube-webos

```bash
# Download IPK
curl -L -o youtube-webos.ipk \
  "https://github.com/FriedChickenButt/youtube-webos/releases/download/0.0.2/youtube.leanback.v4_0.0.2_all.ipk"

# Install
ares-install --device lgtv youtube-webos.ipk
```

### 5. Launch

The app appears as `youtube.leanback.v4` in the TV's app list.

## Notes

- Developer Mode session expires after ~1000 hours. Extend in the app.
- Installed apps are removed if Developer Mode is disabled.
- SSH key is served on port 9991 (HTTP), not 9922 (SSH).
