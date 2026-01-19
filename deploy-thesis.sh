#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    LAYRA SOLO THESIS DEPLOYMENT SCRIPT                         ║
# ║                    GPU + Neo4j + Simple Auth                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    LAYRA SOLO THESIS DEPLOYMENT                             ║"
echo "║                    GPU + Neo4j + Simple Auth                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

# Check if NVIDIA GPU is available
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA GPU detected${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo -e "${RED}✗ No NVIDIA GPU detected. This deployment requires GPU support.${NC}"
    echo -e "${YELLOW}  If you have a GPU, please install NVIDIA drivers and nvidia-container-toolkit.${NC}"
    exit 1
fi

# Check if nvidia-container-toolkit is installed
if docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA Container Toolkit working${NC}"
else
    echo -e "${RED}✗ NVIDIA Container Toolkit not working properly${NC}"
    echo -e "${YELLOW}  Install: sudo apt-get install -y nvidia-container-toolkit${NC}"
    echo -e "${YELLOW}  Then: sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker${NC}"
    exit 1
fi

# Check available disk space
DISK_AVAILABLE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$DISK_AVAILABLE" -lt 100 ]; then
    echo -e "${YELLOW}⚠ Warning: Less than 100GB disk space available. Current: ${DISK_AVAILABLE}GB${NC}"
    echo -e "${YELLOW}  Recommended: 100GB+ for model weights and data${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Sufficient disk space: ${DISK_AVAILABLE}GB available${NC}"
fi

# Check .env.thesis file
echo -e "\n${YELLOW}[2/7] Checking configuration...${NC}"

if [ ! -f ".env.thesis" ]; then
    echo -e "${RED}✗ .env.thesis file not found${NC}"
    echo -e "${YELLOW}  Creating from template...${NC}"
    # Will be created separately
fi

# Verify critical passwords are changed
if grep -q "thesis_password_change_this" .env.thesis 2>/dev/null; then
    echo -e "${RED}✗ Default passwords detected in .env.thesis${NC}"
    echo -e "${YELLOW}  Please change these passwords before deployment:${NC}"
    echo -e "${YELLOW}    - NEO4J_PASSWORD${NC}"
    echo -e "${YELLOW}    - REDIS_PASSWORD${NC}"
    echo -e "${YELLOW}    - MONGODB_ROOT_PASSWORD${NC}"
    echo -e "${YELLOW}    - MINIO_SECRET_KEY${NC}"
    echo -e "${YELLOW}    - SIMPLE_PASSWORD${NC}"
    echo ""
    read -p "Have you changed the default passwords? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}  Please edit .env.thesis and change the passwords, then run this script again.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Configuration verified${NC}"

# Prepare environment
echo -e "\n${YELLOW}[3/7] Preparing environment...${NC}"

# Copy .env.thesis to .env
cp .env.thesis .env
echo -e "${GREEN}✓ Environment configured${NC}"

# Clean up any previous deployment
echo -e "\n${YELLOW}[4/7] Cleaning previous deployment...${NC}"

# Stop and remove existing containers
docker compose -f docker-compose.thesis.yml down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}✓ Previous deployment cleaned${NC}"

# Build and start services
echo -e "\n${YELLOW}[5/7] Building and starting services...${NC}"
echo -e "${BLUE}  This will take 5-10 minutes on first run (downloading models)...${NC}"

# Build and start
docker compose -f docker-compose.thesis.yml up -d --build

echo -e "${GREEN}✓ Services started${NC}"

# Wait for critical services to be healthy
echo -e "\n${YELLOW}[6/7] Waiting for services to be healthy...${NC}"

MAX_WAIT=300  # 5 minutes
ELAPSED=0

echo -e "  Waiting for model weights download (this may take a while)..."
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker ps --filter "name=layra-model-weights-init" --format "{{.Status}}" | grep -q "Exited"; then
        echo -e "${GREEN}✓ Model weights downloaded${NC}"
        break
    fi
    if docker ps --filter "name=layra-model-weights-init" --format "{{.Status}}" | grep -q "Exited (1)"; then
        echo -e "${RED}✗ Model weights download failed${NC}"
        echo -e "${YELLOW}  Check logs: docker compose -f docker-compose.thesis.yml logs model-weights-init${NC}"
        exit 1
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "\n${YELLOW}⚠ Model weights download taking longer than expected${NC}"
    echo -e "${YELLOW}  Check progress: docker compose -f docker-compose.thesis.yml logs -f model-weights-init${NC}"
fi

echo ""
echo "  Waiting for backend health check..."
ELAPSED=0
MAX_WAIT=120  # 2 minutes
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8090/api/v1/health/check &> /dev/null; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "\n${RED}✗ Backend failed to start${NC}"
    echo -e "${YELLOW}  Check logs: docker compose -f docker-compose.thesis.yml logs backend${NC}"
    exit 1
fi

# Verify Neo4j
echo ""
echo "  Waiting for Neo4j..."
ELAPSED=0
MAX_WAIT=60
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker exec layra-neo4j wget --spider -q http://localhost:7474 2>/dev/null; then
        echo -e "${GREEN}✓ Neo4j is healthy${NC}"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "\n${YELLOW}⚠ Neo4j still starting (this is normal for first run)${NC}"
fi

# Final verification
echo -e "\n${YELLOW}[7/7] Verifying deployment...${NC}"

# Check all running containers
RUNNING_CONTAINERS=$(docker compose -f docker-compose.thesis.yml ps --services --filter "status=running" | wc -l)
echo -e "${GREEN}✓ Running containers: ${RUNNING_CONTAINERS}${NC}"

# Display access information
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    LAYRA DEPLOYMENT COMPLETE!                              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}🌐 LAYRA APPLICATION:${NC}"
echo -e "   URL:        ${GREEN}http://localhost:8090${NC}"
echo -e "   Username:   ${GREEN}thesis${NC}"
echo -e "   Password:   ${GREEN}(from .env.thesis - SIMPLE_PASSWORD)${NC}"
echo ""
echo -e "${YELLOW}🔍 NEO4J BROWSER:${NC}"
echo -e "   URL:        ${GREEN}http://localhost:7474${NC}"
echo -e "   Username:   ${GREEN}neo4j${NC}"
echo -e "   Password:   ${GREEN}(from .env.thesis - NEO4J_PASSWORD)${NC}"
echo ""
echo -e "${YELLOW}📊 NEO4J BOLT (for code):${NC}"
echo -e "   URI:        ${GREEN}bolt://neo4j:7687${NC}"
echo -e "   (accessible from within Docker network)"
echo ""
echo -e "${YELLOW}🐳 DOCKER COMMANDS:${NC}"
echo -e "   View logs:     ${CYAN}docker compose -f docker-compose.thesis.yml logs -f${NC}"
echo -e "   Stop:          ${CYAN}docker compose -f docker-compose.thesis.yml down${NC}"
echo -e "   Restart:       ${CYAN}docker compose -f docker-compose.thesis.yml restart${NC}"
echo -e "   Backend shell: ${CYAN}docker exec -it layra-backend bash${NC}"
echo -e "   Neo4j shell:   ${CYAN}docker exec -it layra-neo4j cypher-shell${NC}"
echo ""
echo -e "${YELLOW}📈 RESOURCE USAGE:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    $(docker ps --filter "name=layra-" --format "{{.Names}}")
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ SOLO THESIS DEPLOYMENT READY!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
