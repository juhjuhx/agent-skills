# Bilibili (B站) CDN Troubleshooting from Taiwan

## Root Cause

Bilibili randomly assigns CDN nodes. Some have terrible bandwidth:

| CDN Domain | Typical Speed | Notes |
|:---|:---|:---|
| `upos-hz-mirrorakam.akamaized.net` | 15 MB/s | Fastest — Akamai edge |
| `cn-hk-eq-01-*.bilivideo.com` | 7 MB/s | Medium — HK node |
| `upos-sz-mirroraliov.bilivideo.com` | 1 MB/s | Slowest — often assigned |

**Key insight:** Ping latency ≠ download speed. A 6ms CDN can deliver 1MB/s while a 55ms CDN delivers 7MB/s.

## ISP-Specific Notes (Taiwan)

| ISP | Typical bilibili.com ping | Notes |
|:---|:---|:---|
| 中華電信 (CHT) | 40-80ms | Best routing to mainland |
| 凱擘 (KBtelecom) | 180-220ms | Routes via HK→SGP→CN (bad) |
| 台灣大 (Taiwan Mobile) | 60-100ms | Decent |
| 遠傳 (FarEasTone) | 60-100ms | Decent |

## Solutions (in order of recommendation)

### 1. Greasy Fork CDN Switcher Script (best)
- Install Tampermonkey in browser
- Install: https://greasyfork.org/zh-TW/scripts/500213-bilibili-video-cdn-switcher
- Auto-switches slow CDN to fast CDN

### 2. ccb Script
- https://github.com/Kanda-Akihito-Kun/ccb
- Switch to "Hong Kong" source first

### 3. Manual Hosts File (macOS)
```bash
# Find fast CDN IP
ping upos-hz-mirrorakam.akamaized.net

# Edit hosts
sudo nano /etc/hosts

# Add line (replace with your pinged IP):
<IP> upos-sz-mirroraliov.bilivideo.com

# Flush DNS
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

### 4. Official Speed Test
https://www.bilibili.com/blackboard/video-diagnostics.html

### 5. bilibili.tv (international, anime only)
- 36ms from Taiwan
- Limited content (anime/donghua only)
- No user uploads, no danmaku

## Diagnosis Commands
```bash
# Compare main site vs CDN
ping -c 3 bilibili.com
ping -c 3 static.hdslb.com

# Check routing
traceroute bilibili.com

# Test different DNS
nslookup bilibili.com 8.8.8.8
nslookup bilibili.com 168.95.1.1
```
