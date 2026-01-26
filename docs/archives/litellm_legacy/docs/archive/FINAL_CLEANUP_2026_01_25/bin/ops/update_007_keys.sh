#!/bin/bash
#
# LiteLLM Key Rotation - Update ~/.007
# =====================================
# This script safely updates your ~/.007 file with the new master keys.
#

set -euo pipefail

# Configuration - MUST BE CONFIGURED BEFORE RUNNING
NEW_MASTER_KEY="<NEW_MASTER_KEY>"
NEW_SALT_KEY="<NEW_SALT_KEY>"
OLD_MASTER_KEY="<OLD_MASTER_KEY>"
DOT_007="$HOME/.007"

# Colors
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
RESET='\033[0m'

print_header() {
    echo -e "\n${BLUE}========================================${RESET}"
    echo -e "${BLUE}$1${RESET}"
    echo -e "${BLUE}========================================${RESET}\n"
}

print_step() {
    echo -e "${GREEN}[$1]${RESET} $2"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${RESET}"
}

# Backup .007
print_header "Backing up ~/.007"
if [ -f "$DOT_007" ]; then
    cp "$DOT_007" "${DOT_007}.backup.$(date +%Y%m%d_%H%M%S)"
    print_step 1 "Backup created: ${DOT_007}.backup.$(date +%Y%m%d_%H%M%S)"
else
    echo -e "${RED}ERROR: $DOT_007 not found${RESET}"
    exit 1
fi

# Update or add keys
print_header "Updating ~/.007 with new keys"

# Check if keys exist and update them
if grep -q "^export LITELLM_MASTER_KEY=" "$DOT_007"; then
    print_step 2 "Updating existing LITELLM_MASTER_KEY"
    sed -i "s|^export LITELLM_MASTER_KEY=.*|export LITELLM_MASTER_KEY=\"${NEW_MASTER_KEY}\"|" "$DOT_007"
else
    print_step 2 "Adding new LITELLM_MASTER_KEY"
    echo "export LITELLM_MASTER_KEY=\"${NEW_MASTER_KEY}\"" >> "$DOT_007"
fi

if grep -q "^export LITELLM_SALT_KEY=" "$DOT_007"; then
    print_step 3 "Updating existing LITELLM_SALT_KEY"
    sed -i "s|^export LITELLM_SALT_KEY=.*|export LITELLM_SALT_KEY=\"${NEW_SALT_KEY}\"|" "$DOT_007"
else
    print_step 3 "Adding new LITELLM_SALT_KEY"
    echo "export LITELLM_SALT_KEY=\"${NEW_SALT_KEY}\"" >> "$DOT_007"
fi

# Update test keys to use the new master key
if grep -q "^export LITELLM_SMOKE_TEST_KEY=" "$DOT_007"; then
    print_step 4 "Updating LITELLM_SMOKE_TEST_KEY"
    sed -i "s|^export LITELLM_SMOKE_TEST_KEY=.*|export LITELLM_SMOKE_TEST_KEY=\"${NEW_MASTER_KEY}\"|" "$DOT_007"
fi

if grep -q "^export LITELLM_HEALTH_API_KEY=" "$DOT_007"; then
    print_step 5 "Updating LITELLM_HEALTH_API_KEY"
    sed -i "s|^export LITELLM_HEALTH_API_KEY=.*|export LITELLM_HEALTH_API_KEY=\"${NEW_MASTER_KEY}\"|" "$DOT_007"
fi

if grep -q "^export LITELLM_PROXY_API_KEY=" "$DOT_007"; then
    print_step 6 "Updating LITELLM_PROXY_API_KEY"
    sed -i "s|^export LITELLM_PROXY_API_KEY=.*|export LITELLM_PROXY_API_KEY=\"${NEW_MASTER_KEY}\"|" "$DOT_007"
fi

echo -e "${GREEN}✓${RESET} All keys updated in $DOT_007"

# Show next steps
print_header "Next Steps"

echo -e "${GREEN}NEW MASTER KEY:${RESET} ${NEW_MASTER_KEY}"
echo -e "${GREEN}NEW SALT KEY:${RESET}  ${NEW_SALT_KEY}"
echo ""
print_warning "Keep these keys secure! Do not share or commit."

echo ""
echo "To complete the rotation:"
echo ""
echo "1. Update the database:"
echo "   psql <DATABASE_URL>"
echo ""
echo "   UPDATE \"LiteLLM_VerificationToken\""
echo "   SET token = '${NEW_MASTER_KEY}',"
echo "       updated_at = NOW(),"
echo "       rotation_count = COALESCE(rotation_count, 0) + 1,"
echo "       last_rotation_at = NOW()"
echo "   WHERE token = '${OLD_MASTER_KEY}';"
echo ""
echo "2. Restart the service:"
echo "   sudo systemctl restart litellm.service"
echo ""
echo "3. Verify:"
echo "   sudo systemctl status litellm.service"
echo "   curl -H 'Authorization: Bearer ${NEW_MASTER_KEY}' http://127.0.0.1:4000/healthz"
echo ""
