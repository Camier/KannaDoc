#!/bin/bash
# Import API keys from ~/.007 to .env

SOURCE_FILE="$HOME/.007"
ENV_FILE="/LAB/@thesis/layra/.env"

# Keys to import
KEYS=(
    "ZAI_API_KEY"
    "MOONSHOT_API_KEY"
    "MINIMAX_API_KEY"
    "COHERE_API_KEY"
    "OLLAMA_API_KEY"
)

echo "Importing API keys from ~/.007 to $ENV_FILE..."

for key in "${KEYS[@]}"; do
    # Extract value from source file
    value=$(grep "export $key=" "$SOURCE_FILE" | sed "s/export $key=//;s/\"//g")
    
    if [ -n "$value" ]; then
        # Check if key already exists in .env
        if grep -q "^${key}=" "$ENV_FILE"; then
            # Update existing key
            sed -i "s/^${key}=.*/${key}=${value}/" "$ENV_FILE"
            echo "Updated: $key"
        else
            # Append new key
            echo "${key}=${value}" >> "$ENV_FILE"
            echo "Added: $key"
        fi
    else
        echo "Warning: $key not found in $SOURCE_FILE"
    fi
done

echo "Done!"
