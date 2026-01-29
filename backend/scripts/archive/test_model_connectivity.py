#!/usr/bin/env python3
"""
Test connectivity for all configured LLM models.
Skip gpt-4o as per user request.
"""

import asyncio
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.rag.provider_client import ProviderClient

# Models to test (skip gpt-4o)
MODELS_TO_TEST = [
    "gpt-5.2",
    "deepseek-v3.2",
    "deepseek-r1",
    "kimi-k2-thinking",
    "glm-4.7",
    "glm-4.7-flash",
]

# Test prompt - short, simple, non-controversial
TEST_PROMPT = "Hello, please respond with 'Model [MODEL_NAME] is working'."


async def test_model(model_name: str, timeout: int = 30) -> Dict[str, any]:
    """
    Test a single model by sending a simple prompt.
    Returns a dict with test results.
    """
    print(f"\n{'=' * 60}")
    print(f"Testing model: {model_name}")
    print(f"Start time: {datetime.now().strftime('%H:%M:%S')}")

    result = {
        "model": model_name,
        "success": False,
        "response_time": None,
        "error": None,
        "provider": None,
        "response_sample": None,
    }

    start_time = datetime.now()

    try:
        # Get provider for model
        provider = ProviderClient.get_provider_for_model(model_name)
        result["provider"] = provider

        # Create client
        client = ProviderClient.create_client(model_name)

        # Prepare messages
        messages = [
            {"role": "user", "content": TEST_PROMPT.replace("[MODEL_NAME]", model_name)}
        ]

        # Make API call with timeout
        try:
            chat_completion = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=50,
                    temperature=0.1,
                ),
                timeout=timeout,
            )

            # Extract response
            response_text = chat_completion.choices[0].message.content
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            result["success"] = True
            result["response_time"] = response_time
            result["response_sample"] = (
                response_text[:200] + "..."
                if len(response_text) > 200
                else response_text
            )

            print(f"✓ SUCCESS - Response time: {response_time:.2f}s")
            print(f"  Provider: {provider}")
            print(f"  Response sample: {result['response_sample']}")

        except asyncio.TimeoutError:
            error_msg = f"Request timed out after {timeout}s"
            result["error"] = error_msg
            print(f"✗ TIMEOUT - {error_msg}")
        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg
            print(f"✗ ERROR - {error_msg}")

    except Exception as e:
        error_msg = str(e)
        result["error"] = error_msg
        print(f"✗ SETUP ERROR - {error_msg}")

    return result


async def main():
    """Test all models sequentially."""
    print("\n" + "=" * 60)
    print("LAYRA Model Connectivity Test")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Models to test: {', '.join(MODELS_TO_TEST)}")
    print("=" * 60)

    results = []

    for model in MODELS_TO_TEST:
        result = await test_model(model)
        results.append(result)
        # Small delay between tests to avoid rate limits
        await asyncio.sleep(2)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\nSuccessful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"  ✓ {r['model']} ({r['provider']}): {r['response_time']:.2f}s")

    if failed:
        print(f"\nFailed: {len(failed)}/{len(results)}")
        for r in failed:
            print(f"  ✗ {r['model']}: {r['error']}")

    # Return exit code based on failures
    if len(failed) > 0:
        print("\n❌ Some models failed connectivity test.")
        sys.exit(1)
    else:
        print("\n✅ All models passed connectivity test!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
