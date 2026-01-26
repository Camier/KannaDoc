# LiteLLM Docker Deployment Guide

This guide describes **how this repo runs LiteLLM with Docker Compose**. LiteLLM behavior references the official docs.

## Official Reference
- Docker quick start: https://docs.litellm.ai/docs/proxy/docker_quick_start
- Proxy config: https://docs.litellm.ai/docs/proxy/configs
- Health endpoints: https://docs.litellm.ai/docs/proxy/health

## Quick Start (This Repo)

```bash
# Copy the example env file
# Full template (recommended)
cp .env.example .env

# Or minimal docker template
# cp .env.docker.example .env

# Edit .env with your values
vim .env

# Start services
docker-compose up -d

# Verify containers
docker-compose ps

# Health check (official endpoint)
curl http://127.0.0.1:4001/health/liveliness
```

## Services & Ports
See `docker-compose.yml` for the authoritative service list and port mappings.
By default, the proxy ports are exposed on all interfaces. For local-only
access, bind to `127.0.0.1` and ensure firewall rules are in place.

### Firewall (Best Practices + Examples)
If you expose ports publicly, restrict access at the host firewall.

Docker installs its own firewall rules for port publishing and network isolation. Avoid editing Docker-managed chains directly. Published ports are exposed externally by default; bind to `127.0.0.1` if you only need local access.

If you must filter access to published container ports:
- iptables backend: add allow/deny rules to the `DOCKER-USER` chain (processed before Docker's rules).
- nftables backend: Docker does not create `DOCKER-USER`; create your own table/base chains with the same hook points and set priorities to order your rules relative to Docker's base chains.
- UFW: Docker-published ports bypass UFW's normal `INPUT`/`OUTPUT` rules due to Docker's NAT/forwarding; use `DOCKER-USER` (iptables) or nftables guidance below.

**iptables (recommended with Docker; allow a single client IP):**
```bash
sudo iptables -A DOCKER-USER -p tcp -s <YOUR_IP> --dport 4000 -j ACCEPT
sudo iptables -A DOCKER-USER -p tcp -s <YOUR_IP> --dport 4001 -j ACCEPT
sudo iptables -A DOCKER-USER -p tcp --dport 4000 -j DROP
sudo iptables -A DOCKER-USER -p tcp --dport 4001 -j DROP
```

**UFW (host firewall only; does not cover Docker-published ports without DOCKER-USER):**
```bash
sudo ufw allow from <YOUR_IP> to any port 4000 proto tcp
sudo ufw allow from <YOUR_IP> to any port 4001 proto tcp
sudo ufw deny 4000/tcp
sudo ufw deny 4001/tcp
```

**nftables (allow a single client IP):**
```bash
table inet litellm-filter {
  chain forward-pre {
    type filter hook forward priority filter; policy accept;
    ip saddr <YOUR_IP> tcp dport {4000,4001} accept
    tcp dport {4000,4001} drop
  }
}
```

Persist firewall rules per your distro (for example, Debian uses `/etc/nftables.conf` with `nftables.service` enabled).

## Common Operations

```bash
# Logs
docker-compose logs -f litellm

# Restart
docker-compose restart litellm

# Stop containers (keeps volumes)
docker-compose stop

# Stop and remove containers (keeps volumes)
docker-compose down
```

## Configuration Updates

```bash
# Edit config.yaml
vim config.yaml

# Restart to apply changes
docker-compose restart litellm
```

## Admin UI
The Admin UI is served at `/ui` when a database is configured (official). See:
https://docs.litellm.ai/docs/proxy/ui
