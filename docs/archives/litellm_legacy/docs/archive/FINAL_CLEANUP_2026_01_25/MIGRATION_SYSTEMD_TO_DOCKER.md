# Systemd to Docker Migration Guide

This document describes the migration from systemd/conda deployment to Docker Compose.

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2
- Existing systemd deployment running

## Pre-Migration Checklist

- [ ] Backup database using `python bin/backup_db.py`
- [ ] Create `.env` from `.env.docker.example` and update secrets
- [ ] Validate with `bin/validate_migration.sh`
- [ ] Stop non-critical services

## Migration Steps

### 1. Pre-Migration Backup

```bash
# Run backup
python bin/backup_db.py

# Note backup location
ls -lt state/archive/backups/ | head -5
```

### 2. Stop Systemd Services

```bash
# Stop and disable main service
systemctl --user stop litellm.service
systemctl --user disable litellm.service

# Verify ports are free
lsof -i :4000  # Should be empty
```

### 3. Start Docker Services

```bash
# Pull images
docker-compose pull

# Start services
docker-compose up -d

# Verify status
docker-compose ps
bin/health_check_docker.sh
```

### 4. Verify Functionality

```bash
# Test API
curl http://127.0.0.1:4000/healthz

# Run probe
set -a
source .env
set +a
~/.conda/envs/litellm/bin/python bin/probe_capabilities.py
```

### 5. Update Monitoring Services

```bash
# Switch to Docker-aware services
systemctl --user daemon-reload
systemctl --user disable litellm-healthcheck.timer
systemctl --user enable litellm-healthcheck.timer  # Docker version
systemctl --user start litellm-healthcheck.timer
```

## Rollback

If issues occur:

```bash
# Quick rollback
bin/rollback_to_systemd.sh

# Manual rollback
docker-compose down
systemctl --user enable litellm.service
systemctl --user start litellm.service
```

## Post-Migration Tasks

- [ ] Monitor logs for 24 hours
- [ ] Verify backups run with new script
- [ ] Update any external references to service URLs
- [ ] Remove old conda environment (after verification period)

## Troubleshooting

### Port conflicts

If ports are in use:
```bash
# Check what's using the port
lsof -i :4000

# Stop conflicting service
systemctl --user stop litellm.service
```

### Database connection issues

```bash
# Check PostgreSQL container
docker-compose logs postgres

# Verify database exists
docker exec -it litellm-postgres psql -U litellm -d litellm -c "\l"
```

### Service not starting

```bash
# Check logs
docker-compose logs litellm

# Validate config
docker-compose config
```
