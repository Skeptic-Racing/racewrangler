# Pi 5 Server Setup Guide
## RaceWrangler — Event Server Configuration
## Version: April 2026

This document covers how to set up the Raspberry Pi 5 as the RaceWrangler event server:
OS image, software installation, WiFi access point, DNS, NTP, and service startup.

---

## 1. Hardware

| Component | Specification |
|-----------|---------------|
| Board | Raspberry Pi 5 (4 GB or 8 GB RAM recommended) |
| Storage | 32 GB+ microSD (Class 10 / A2 rated) |
| Power | Official Pi 5 27W USB-C PSU |
| Cooling | Active cooler (Pi 5 throttles without cooling under OCR load) |
| WiFi | Built-in 802.11ac (used as timing AP) |

---

## 2. OS Installation

1. Download **Raspberry Pi OS Lite (64-bit)** from raspberrypi.com
2. Flash to microSD with **Raspberry Pi Imager**
3. In the Imager advanced settings before flashing:
   - Set hostname: `racewrangler`
   - Enable SSH with a password or public key
   - **Do not configure WiFi here** — wlan0 will be configured as an AP, not a client

---

## 3. System Dependencies

```bash
sudo apt update && sudo apt upgrade -y

# Network stack
sudo apt install -y hostapd dnsmasq avahi-daemon

# NTP
sudo apt install -y chrony

# Python / backend
sudo apt install -y python3-pip python3-venv git

# PaddleOCR dependencies
sudo apt install -y libgomp1 libopenblas-dev libatlas-base-dev

# Camera (for future Pi Zero testing from Pi 5 — optional)
sudo apt install -y python3-picamera2
```

---

## 4. Network Configuration

The Pi 5 acts as a WiFi access point for all timing devices. It does not connect to any
upstream WiFi network during an event.

### 4.1 Static IP on wlan0

Edit `/etc/dhcpcd.conf` and add at the end:

```
interface wlan0
    static ip_address=192.168.10.1/24
    nohook wpa_supplicant
```

### 4.2 hostapd — WiFi Access Point

Create `/etc/hostapd/hostapd.conf`:

```ini
interface=wlan0
driver=nl80211
ssid=RaceWrangler-Timing
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=CHANGE_ME_BEFORE_EVENT
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

Enable and configure:

```bash
sudo systemctl unmask hostapd
sudo systemctl enable hostapd

# Tell hostapd where its config is:
sudo sed -i 's|#DAEMON_CONF=""|\DAEMON_CONF="/etc/hostapd/hostapd.conf"|' \
    /etc/default/hostapd
```

**Change `wpa_passphrase` before each event.** The same password goes in the RaceSpy
firmware config (`/etc/racespy/config.json`).

### 4.3 dnsmasq — DHCP and DNS

Back up and replace `/etc/dnsmasq.conf`:

```ini
# Interface
interface=wlan0
bind-interfaces

# DHCP pool
dhcp-range=192.168.10.50,192.168.10.150,24h
dhcp-option=3,192.168.10.1   # Default gateway
dhcp-option=6,192.168.10.1   # DNS server (Pi 5 itself)

# DNS — resolve racewrangler and racewrangler.local to this server
address=/racewrangler/192.168.10.1
address=/racewrangler.local/192.168.10.1

# Prevent forwarding short names upstream
domain-needed
bogus-priv
```

```bash
sudo systemctl enable dnsmasq
```

### 4.4 avahi-daemon — mDNS Fallback

avahi-daemon is installed by default on Raspberry Pi OS. Verify the hostname matches:

```bash
hostnamectl set-hostname racewrangler
```

avahi broadcasts `racewrangler.local` over mDNS. Devices that do not use DHCP-assigned DNS
(e.g., statically configured phones) can still reach the server at `http://racewrangler.local/`.

```bash
sudo systemctl enable avahi-daemon
```

### 4.5 Internet Access Blocking (Optional)

If the Pi 5 has a second network interface with internet access (e.g., USB-to-Ethernet for
pre-event software updates), prevent timing network clients from routing through it:

```bash
sudo iptables -A FORWARD -i wlan0 -o eth0 -j DROP
sudo iptables-save | sudo tee /etc/iptables/rules.v4
sudo apt install -y iptables-persistent
```

**Not required for the 2-weekend test** — the Pi 5 will not have a WAN uplink at the event.

---

## 5. NTP Server (chrony)

Edit `/etc/chrony/chrony.conf`. Add or replace the NTP server section:

```
# Allow NTP clients on the timing network
allow 192.168.10.0/24

# If internet is available at setup time, sync from public NTP
server time.cloudflare.com iburst

# If no internet, use local hardware clock (less accurate but better than nothing)
local stratum 10

# RaceSpies sync aggressively
minpoll 3
maxpoll 4
```

```bash
sudo systemctl enable chrony
```

**Pre-event:** Connect the Pi 5 to internet briefly before the event to sync chrony to
public NTP. Disconnect before the event begins. Chrony will coast on its synchronized
clock during the event.

---

## 6. RaceWrangler Backend Installation

```bash
cd /opt
sudo git clone https://github.com/OWNER/racewrangler.git
sudo chown -R pi:pi racewrangler
cd racewrangler

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# PaddleOCR (large download, ~1 GB)
pip install paddlepaddle paddleocr
```

### 6.1 Environment Configuration

Create `/opt/racewrangler/.env`:

```
DATABASE_URL=sqlite:////opt/racewrangler/data/racewrangler.db
DATA_DIR=/opt/racewrangler/data
CORS_ORIGINS=*
```

```bash
mkdir -p /opt/racewrangler/data
```

### 6.2 Systemd Service

Create `/etc/systemd/system/racewrangler.service`:

```ini
[Unit]
Description=RaceWrangler Backend
After=network-online.target dnsmasq.service chrony.service
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/opt/racewrangler
ExecStart=/opt/racewrangler/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5
Environment=PYTHONPATH=/opt/racewrangler

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable racewrangler
```

---

## 7. Service Startup Order

Systemd ensures services start in the correct order:

```
hostapd  →  dnsmasq  →  avahi-daemon  →  chrony  →  racewrangler
```

This ordering guarantees that by the time the backend starts:
- The AP is up (RaceSpies can connect)
- DNS is resolving `racewrangler` correctly
- NTP is serving (RaceSpies can sync clocks)
- The backend is reachable at `http://racewrangler/`

---

## 8. Verification

Run this after boot to confirm everything is working:

```bash
# 1. Check all services are active
systemctl status hostapd dnsmasq avahi-daemon chrony racewrangler

# 2. Verify AP is broadcasting
iwconfig wlan0   # Should show mode:Master

# 3. Verify DNS is resolving
dig @192.168.10.1 racewrangler    # Should return 192.168.10.1

# 4. Verify NTP is serving
chronyc clients   # Should show connected clients once RaceSpies are up

# 5. Verify backend responds
curl http://localhost/api/v1/health
```

**Field test from a phone:**
1. Connect phone to `RaceWrangler-Timing` WiFi
2. Open browser and go to `http://racewrangler/`
3. The RaceWrangler UI should load

If the UI does not load, try `http://racewrangler.local/` (mDNS fallback).

---

## 9. Pre-Event Checklist

- [ ] Change `wpa_passphrase` in hostapd.conf and matching firmware config on all RaceSpies
- [ ] Sync chrony to public NTP (`chronyc tracking` — offset should be < 100ms)
- [ ] Verify backend health endpoint responds
- [ ] Load entry CSV and confirm competitor count
- [ ] Test one RaceSpy boot: LED sequence green → blue → green+blue+yellow (armed)
- [ ] Test trigger: break beam by hand, confirm timing event appears in admin UI

---

## 10. For Larger Events (Future Reference)

For events with hundreds of competitors/spectators who also need WiFi:

- The timing network (`RaceWrangler-Timing`) stays dedicated to timing devices only
- Add a second AP for competitors/spectators: **Ubiquiti UniFi U6 Mesh** (~$180) or
  **TP-Link Omada EAP670** (~$100) — both handle 200+ clients outdoors
- If workers need to reach `http://racewrangler/` from the competitor network, add a
  second network interface to the Pi 5 (USB-to-Ethernet adapter), assign it a static IP
  on the competitor network, and configure the competitor AP's DNS to resolve `racewrangler`
  to that IP
- See the event-day runbook for multi-network topology setup

---

## 11. Backup and Recovery

### 11.1 Database Backup During Event

```bash
# Run from the Pi 5 or over SSH from a connected laptop
sqlite3 /opt/racewrangler/data/racewrangler.db ".backup /tmp/backup-$(date +%H%M).db"
```

Run this backup every hour during a live event. Copy the `.db` file to a USB drive.

### 11.2 Full SD Card Image

Before each event, image the SD card:

```bash
# On a laptop (macOS/Linux)
sudo dd if=/dev/sdX of=racewrangler-$(date +%Y%m%d).img bs=4M status=progress
```

Restoring from this image returns the Pi 5 to a fully configured state in < 10 minutes.
