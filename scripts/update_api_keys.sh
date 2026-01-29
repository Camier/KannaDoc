#!/bin/bash
# Update .env with fresh API keys from ~/.007

set -e

ENV_FILE="/LAB/@thesis/layra/.env"
SOURCE_FILE="$HOME/.007"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: $SOURCE_FILE not found"
    exit 1
fi

echo "Importing API keys from ~/.007 to .env..."

# Source the API keys
source "$SOURCE_FILE"

# Function to update or append env var
update_env() {
    local key=$1
    local value=$2
    
    if grep -q "^${key}=" "$ENV_FILE"; then
        # Update existing
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        echo "✅ Updated $key"
    else
        # Append new
        echo "${key}=${value}" >> "$ENV_FILE"
        echo "✅ Added $key"
    fi
}

# Update existing keys
[ -n "$OPENAI_API_KEY" ] && update_env "OPENAI_API_KEY" "$OPENAI_API_KEY"
[ -n "$DEEPSEEK_API_KEY" ] && update_env "DEEPSEEK_API_KEY" "$DEEPSEEK_API_KEY"

# Add new provider keys
[ -n "$ZHIPUAI_API_KEY" ] && update_env "ZHIPUAI_API_KEY" "$ZHIPUAI_API_KEY"
[ -n "$MOONSHOT_API_KEY" ] && update_env "MOONSHOT_API_KEY" "$MOONSHOT_API_KEY"
[ -n "$MINIMAX_API_KEY" ] && update_env "MINIMAX_API_KEY" "$MINIMAX_API_KEY"
[ -n "$COHERE_API_KEY" ] && update_env "COHERE_API_KEY" "$COHERE_API_KEY"
[ -n "$OLLAMA_CLOUD_API_KEY" ] && update_env "OLLAMA_API_KEY" "$OLLAMA_CLOUD_API_KEY"

# Optional: Anthropic and Gemini if available
[ -n "$ANTHROPIC_API_KEY" ] && update_env "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY"
[ -n "$GEMINI_API_KEY" ] && update_env "GEMINI_API_KEY" "$GEMINI_API_KEY"

echo ""
echo "✅ API keys updated successfully!"
echo "Available providers: OpenAI, DeepSeek, Zhipu, Moonshot, MiniMax, Cohere, Ollama"
