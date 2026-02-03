# LAYRA - Makefile
# Quick shortcuts for development and deployment

.PHONY: up down logs restart build clean reset status health test test-frontend test-all help

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m # No Color

# Default target
help:
	@echo ""
	@echo "LAYRA - Quick Commands"
	@echo "====================="
	@echo ""
	@echo "  ${GREEN}make up${NC}        - Start all services (detached) - Standard GPU mode"
	@echo "  ${GREEN}make down${NC}      - Stop all services"
	@echo "  ${GREEN}make restart${NC}   - Restart all services"
	@echo ""
	@echo "  ${GREEN}make up-jina${NC}   - Start Jina API mode (no GPU)"
	@echo "  ${GREEN}make up-thesis${NC} - Start Thesis/Solo mode"
	@echo "  ${GREEN}make up-gpu${NC}    - Start GPU optimized mode"
	@echo ""
	@echo "  ${GREEN}make logs${NC}      - View logs (follow mode)"
	@echo "  ${GREEN}make logs-backend${NC}  - View backend logs only"
	@echo "  ${GREEN}make logs-frontend${NC} - View frontend logs only"
	@echo ""
	@echo "  ${GREEN}make reset${NC}     - Stop, remove volumes, start fresh"
	@echo "  ${GREEN}make clean${NC}     - Remove all containers, volumes, images"
	@echo ""
	@echo "  ${GREEN}make status${NC}    - Show service status"
	@echo "  ${GREEN}make health${NC}    - Check API health"
	@echo ""
	@echo "  ${GREEN}make build${NC}     - Rebuild all images"
	@echo "  ${GREEN}make build-backend${NC} - Rebuild backend only"
	@echo "  ${GREEN}make build-frontend${NC} - Rebuild frontend only"
	@echo ""
	@echo "  ${GREEN}make ssh-backend${NC} - SSH into backend container"
	@echo "  ${GREEN}make ssh-model${NC}   - SSH into model-server container"
	@echo ""
	@echo "  ${GREEN}make test${NC}       - Run backend tests (pytest)"
	@echo "  ${GREEN}make test-frontend${NC} - Run frontend tests (vitest)"
	@echo "  ${GREEN}make test-all${NC}    - Run all tests"
	@echo "  ${GREEN}make health${NC}     - Check API health"
	@echo "  ${GREEN}make help${NC}       - Show this help message"
	@echo ""

# Start all services (Standard GPU mode)
up:
	@echo "${YELLOW}Starting LAYRA (Standard GPU mode)...${NC}"
	./scripts/compose-clean up -d

# Start Jina API mode (no GPU)
up-jina:
	@echo "${YELLOW}Starting LAYRA (Jina API mode - no GPU)...${NC}"
	./scripts/compose-clean -f docker-compose-no-local-embedding.yml up -d

# Start Thesis/Solo mode
up-thesis:
	@echo "${YELLOW}Starting LAYRA (Thesis/Solo mode)...${NC}"
	@if [ -f .env.thesis ]; then \
		cp .env.thesis .env; \
		echo "${GREEN}Copied .env.thesis to .env${NC}"; \
	else \
		echo "${RED}Warning: .env.thesis not found. Using existing .env${NC}"; \
	fi
	docker compose -f docker-compose.thesis.yml up -d

# Start GPU optimized mode
up-gpu:
	@echo "${YELLOW}Starting LAYRA (GPU optimized mode)...${NC}"
	./scripts/compose-clean -f docker-compose.gpu.yml up -d

# Stop all services
down:
	@echo "${YELLOW}Stopping LAYRA...${NC}"
	./scripts/compose-clean down

# Restart all services
restart: down up
	@echo "${GREEN}LAYRA restarted!${NC}"

# View logs (follow mode)
logs:
	./scripts/compose-clean logs -f

# View backend logs
logs-backend:
	./scripts/compose-clean logs -f backend

# View frontend logs
logs-frontend:
	./scripts/compose-clean logs -f frontend

# Reset everything (destroy volumes)
reset:
	@echo "${YELLOW}Resetting LAYRA (this will DELETE all data!)...${NC}"
	@read -p "Are you sure? [y/N] " -n 1 -r; echo; if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/compose-clean down -v && ./scripts/compose-clean up -d; \
		echo "${GREEN}LAYRA reset complete!${NC}"; \
	fi

# Clean everything (remove containers, volumes, networks)
clean:
	@echo "${RED}WARNING: This will remove ALL containers, volumes, and networks!${NC}"
	@read -p "Are you sure? [y/N] " -n 1 -r; echo; if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/compose-clean down -v --remove-orphans && \
		docker system prune -af && \
		echo "${GREEN}Cleanup complete!${NC}"; \
	fi

# Show service status
status:
	@./scripts/compose-clean ps

# Check API health
health:
	@echo "Checking API health..."
	@echo "Note: Backend health checked through Nginx (port 8090)"
	@curl -s http://localhost:8090/api/v1/health/check > /dev/null && \
		echo "${GREEN}Backend: OK${NC}" || \
		echo "${RED}Backend: FAIL (check if services are running)${NC}"
	@curl -s http://localhost:8090/ > /dev/null && \
		echo "${GREEN}Frontend: OK${NC}" || \
		echo "${RED}Frontend: FAIL${NC}"
	@curl -s http://localhost:9000/minio/health/live > /dev/null && \
		echo "${GREEN}MinIO: OK${NC}" || \
		echo "${RED}MinIO: FAIL${NC}"

# Rebuild all images
build:
	@echo "${YELLOW}Rebuilding all images...${NC}"
	./scripts/compose-clean build --no-cache

# Rebuild backend only
build-backend:
	@echo "${YELLOW}Rebuilding backend...${NC}"
	./scripts/compose-clean build backend --no-cache

# Rebuild frontend only
build-frontend:
	@echo "${YELLOW}Rebuilding frontend...${NC}"
	./scripts/compose-clean build frontend --no-cache

# SSH into backend container
ssh-backend:
	docker exec -it layra-backend /bin/bash

# SSH into model-server container
ssh-model:
	docker exec -it layra-model-server /bin/bash

# Run backend tests
test:
	@echo "${YELLOW}Running backend tests...${NC}"
	cd backend && PYTHONPATH=. pytest

# Run frontend tests
test-frontend:
	@echo "${YELLOW}Running frontend tests...${NC}"
	cd frontend && npm run test:run

# Run all tests
test-all: test test-frontend
