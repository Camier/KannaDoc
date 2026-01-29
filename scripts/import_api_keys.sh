#!/bin/bash
# Import API keys from ~/.007 into Layra .env file

set -e

LAYRA_ENV="/LAB/@thesis/layra/.env"
SOURCE_FILE="$HOME/.007"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "❌ Error: $SOURCE_FILE not found"
    exit 1
fi

if [ ! -f "$LAYRA_ENV" ]; then
    echo "❌ Error: $LAYRA_ENV not found"
    exit 1
fi

echo "📋 Importing API keys from $SOURCE_FILE to $LAYRA_ENV"
echo

# Source the keys
source "$SOURCE_FILE"

# Update .env file
if grep -q "^OPENAI_API_KEY=" "$LAYRA_ENV"; then
    echo "🔄 Updating OPENAI_API_KEY..."
    sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_API_KEY}|" "$LAYRA_ENV"
else
    echo "⚠️ OPENAI_API_KEY not found in .env"
fi

if grep -q "^DEEPSEEK_API_KEY=" "$LAYRA_ENV"; then
    echo "🔄 Updating DEEPSEEK_API_KEY..."
    sed -i "s|^DEEPSEEK_API_KEY=.*|DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}|" "$LAYRA_ENV"
else
    echo "⚠️ DEEPSEEK_API_KEY not found in .env"
fi

echo
echo "✅ API keys imported successfully!"
echo
echo "📝 Verify keys are set:"
echo "   OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."
echo "   DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:0:20}..."
