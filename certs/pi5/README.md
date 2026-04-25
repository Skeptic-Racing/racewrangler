# Pi5 TLS Certificates

`racewrangler-cert.pem` is committed here and auto-detected by `setup-sd-card.sh`.

`racewrangler-key.pem` is excluded from git (see `.gitignore`). Place your private key
here locally before running `setup-sd-card.sh` to provision HTTPS on a fresh SD card.

## IP binding note

The committed cert includes `IP:192.168.0.144` as a SAN. If the Pi5 is assigned a
different IP at a new venue, browsers will reject the cert. You have two options:

- **Reserve the same IP** via DHCP on your router/hotspot (recommended for events).
- **Regenerate the cert** for the new IP using mkcert:

```bash
# Adjust IPs/hostnames as needed
mkcert -cert-file certs/pi5/racewrangler-cert.pem \
       -key-file  certs/pi5/racewrangler-key.pem \
       racewrangler.local racewrangler localhost 192.168.0.144 127.0.0.1
```

The mkcert root CA must already be installed on every client device that needs to trust
the cert (`mkcert -install` on each machine, or distribute `rootCA.pem` manually for
iOS/Android).
