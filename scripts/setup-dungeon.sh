#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🎲 Hermes Dungeon Server — Setup Wizard          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is required but not installed.${NC}"
    exit 1
fi

# Check hermes-base image
if ! docker image inspect hermes-base:latest &> /dev/null; then
    echo -e "${YELLOW}⚠️  Image 'hermes-base:latest' not found locally.${NC}"
    echo "   Make sure you have Hermes installed and the image is available."
    echo "   If you built it from source, tag it: docker tag <your-image> hermes-base:latest"
    exit 1
fi

# Ask for dungeon name
read -rp "🗡️  Dungeon name (default: dungeon): " DUNGEON_NAME
DUNGEON_NAME="${DUNGEON_NAME:-dungeon}"

# Ask for data directory
DEFAULT_DATA_DIR="$HOME/.hermes/${DUNGEON_NAME}_container"
read -rp "📁 Data directory (default: $DEFAULT_DATA_DIR): " DATA_DIR
DATA_DIR="${DATA_DIR:-$DEFAULT_DATA_DIR}"

# Ask for scripts directory
DEFAULT_SCRIPTS_DIR="$HOME/scripts"
read -rp "📁 Scripts directory for entrypoint (default: $DEFAULT_SCRIPTS_DIR): " SCRIPTS_DIR
SCRIPTS_DIR="${SCRIPTS_DIR:-$DEFAULT_SCRIPTS_DIR}"

# Create directories
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/campaign_backups"
mkdir -p "$DATA_DIR/campaigns"
mkdir -p "$DATA_DIR/campaigns_data"
mkdir -p "$DATA_DIR/sessions"
mkdir -p "$DATA_DIR/cron"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/hooks"
mkdir -p "$DATA_DIR/memories"
mkdir -p "$DATA_DIR/skills"
mkdir -p "$DATA_DIR/home"
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$DATA_DIR/session_backups"
mkdir -p "$DATA_DIR/.persistence_recovery"

# Copy templates
echo -e "${BLUE}📄 Copying templates...${NC}"

# SOUL.md
cp "$REPO_DIR/templates/SOUL.md" "$DATA_DIR/SOUL.md"

# Persistence scripts
cp "$REPO_DIR/scripts/session_resume.py" "$DATA_DIR/scripts/"
cp "$REPO_DIR/scripts/campaign_state.py" "$DATA_DIR/scripts/"
cp "$REPO_DIR/scripts/cron-auto-save.sh" "$DATA_DIR/scripts/"
cp "$REPO_DIR/scripts/cron-daily-loader.sh" "$DATA_DIR/scripts/"
chmod +x "$DATA_DIR/scripts/"*.sh
echo -e "${GREEN}   ✓ Persistence scripts (session_resume.py, campaign_state.py, cron jobs)${NC}"

# Campaign files (example canonical campaign)
if [ ! -f "$DATA_DIR/campaigns/the_lost_mine.json" ]; then
    cp "$REPO_DIR/templates/campaigns/the_lost_mine.json" "$DATA_DIR/campaigns/"
    echo -e "${GREEN}   ✓ Example campaign: The Lost Mine of Phandelver${NC}"
fi
if [ ! -f "$DATA_DIR/campaigns_data/the_lost_mine.json" ]; then
    cp "$REPO_DIR/templates/campaigns_data/the_lost_mine.json" "$DATA_DIR/campaigns_data/"
fi
if [ ! -f "$DATA_DIR/campaign_state.json" ]; then
    cp "$REPO_DIR/templates/campaign_state.json" "$DATA_DIR/campaign_state.json"
    echo -e "${GREEN}   ✓ campaign_state.json initial${NC}"
fi

# config.yaml — only if not exists
if [ ! -f "$DATA_DIR/config.yaml" ]; then
    cp "$REPO_DIR/templates/config.yaml" "$DATA_DIR/config.yaml"
    echo -e "${GREEN}   ✓ config.yaml${NC}"
else
    echo -e "${YELLOW}   ⏭ config.yaml already exists, skipping${NC}"
fi

# .env
if [ ! -f "$DATA_DIR/.env" ]; then
    cp "$REPO_DIR/templates/.env.example" "$DATA_DIR/.env"
    echo -e "${GREEN}   ✓ .env (example) — EDIT THIS FILE WITH YOUR API KEYS${NC}"
else
    echo -e "${YELLOW}   ⏭ .env already exists, skipping${NC}"
fi

# entrypoint.sh
ENTRYPOINT_PATH="$SCRIPTS_DIR/entrypoint_${DUNGEON_NAME}.sh"
cp "$REPO_DIR/templates/entrypoint.sh" "$ENTRYPOINT_PATH"
chmod +x "$ENTRYPOINT_PATH"
echo -e "${GREEN}   ✓ entrypoint.sh → $ENTRYPOINT_PATH${NC}"

# Ask for model/API configuration
echo ""
echo -e "${BLUE}⚙️  Model Configuration${NC}"
read -rp "   Default model (default: deepseek-chat): " MODEL
MODEL="${MODEL:-deepseek-chat}"
read -rp "   Provider (default: deepseek): " PROVIDER
PROVIDER="${PROVIDER:-deepseek}"
read -rp "   Base URL (default: https://api.deepseek.com/v1): " BASE_URL
BASE_URL="${BASE_URL:-https://api.deepseek.com/v1}"

# Update config.yaml with model settings
sed -i "s|default: deepseek-chat|default: $MODEL|" "$DATA_DIR/config.yaml"
sed -i "s|provider: deepseek|provider: $PROVIDER|" "$DATA_DIR/config.yaml"
sed -i "s|base_url: https://api.deepseek.com/v1|base_url: $BASE_URL|" "$DATA_DIR/config.yaml"

# Timezone
read -rp "   Timezone (default: Europe/Madrid): " TZ_VAL
TZ_VAL="${TZ_VAL:-Europe/Madrid}"
sed -i "s|timezone: Europe/Madrid|timezone: $TZ_VAL|" "$DATA_DIR/config.yaml"

echo ""
echo -e "${BLUE}🐳 Creating Docker container...${NC}"

# Stop and remove existing container if exists
if docker ps -a --format '{{.Names}}' | grep -q "^${DUNGEON_NAME}$"; then
    echo -e "${YELLOW}   Container '$DUNGEON_NAME' already exists. Removing...${NC}"
    docker stop "$DUNGEON_NAME" &>/dev/null || true
    docker rm "$DUNGEON_NAME" &>/dev/null || true
fi

docker run -d \
    --name "$DUNGEON_NAME" \
    --restart always \
    -e TZ="$TZ_VAL" \
    -v "$DATA_DIR:/opt/data" \
    -v "$ENTRYPOINT_PATH:/entrypoint.sh" \
    hermes-base:latest \
    bash /entrypoint.sh

echo -e "${GREEN}   ✓ Container '$DUNGEON_NAME' started${NC}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🎉 Dungeon Server Ready!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📁 Data directory:    ${BLUE}$DATA_DIR${NC}"
echo -e "📜 Entrypoint:        ${BLUE}$ENTRYPOINT_PATH${NC}"
echo -e "🐳 Container name:    ${BLUE}$DUNGEON_NAME${NC}"
echo -e "🧠 Model:             ${BLUE}$MODEL ($PROVIDER)${NC}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT NEXT STEPS:${NC}"
echo -e "   1. Edit your API keys: ${BLUE}nano $DATA_DIR/.env${NC}"
echo -e "   2. Customize your DM:   ${BLUE}nano $DATA_DIR/SOUL.md${NC}"
echo -e "   3. Restart container:   ${BLUE}docker restart $DUNGEON_NAME${NC}"
echo -e "   4. Watch logs:          ${BLUE}docker logs -f $DUNGEON_NAME${NC}"
echo ""
echo -e "🎲 Happy adventuring!"
