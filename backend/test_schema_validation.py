#!/usr/bin/env python3
"""Test script to verify UserMessage schema validation."""

# Simulate the schema validation
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

class UserMessage(BaseModel):
    """User message in a conversation or workflow."""
    conversation_id: str = Field(..., min_length=1)
    parent_id: str = Field(default="", description="Parent message ID, empty string for root")
    user_message: str = Field(..., min_length=1)
    temp_db_id: Optional[str] = Field(default="", description="Temporary knowledge base ID from file upload")

# Test cases
test_cases = [
    {
        "name": "Valid request with all fields",
        "data": {
            "conversation_id": "user_123",
            "parent_id": "",
            "user_message": "Hello",
            "temp_db_id": ""
        }
    },
    {
        "name": "Valid request without temp_db_id",
        "data": {
            "conversation_id": "user_456",
            "parent_id": "root",
            "user_message": "Hello"
        }
    },
    {
        "name": "Invalid - empty conversation_id",
        "data": {
            "conversation_id": "",
            "parent_id": "",
            "user_message": "Hello",
            "temp_db_id": ""
        },
        "should_fail": True
    },
    {
        "name": "Invalid - empty user_message",
        "data": {
            "conversation_id": "user_789",
            "parent_id": "",
            "user_message": "",
            "temp_db_id": ""
        },
        "should_fail": True
    },
    {
        "name": "Valid request with temp_db_id",
        "data": {
            "conversation_id": "user_000",
            "parent_id": "parent_123",
            "user_message": "What is this?",
            "temp_db_id": "temp_base_123"
        }
    }
]

# Run tests
print("Running UserMessage schema validation tests...\n")
passed = 0
failed = 0

for test in test_cases:
    try:
        msg = UserMessage(**test["data"])
        if test.get("should_fail"):
            print(f"❌ FAILED: {test['name']}")
            print(f"   Expected validation error but got: {msg}")
            failed += 1
        else:
            print(f"✅ PASSED: {test['name']}")
            print(f"   conversation_id={msg.conversation_id}, parent_id={msg.parent_id}, "
                  f"user_message={msg.user_message}, temp_db_id={msg.temp_db_id}")
            passed += 1
    except ValidationError as e:
        if test.get("should_fail"):
            print(f"✅ PASSED: {test['name']}")
            print(f"   Correctly rejected with validation error")
            passed += 1
        else:
            print(f"❌ FAILED: {test['name']}")
            print(f"   Unexpected validation error: {e}")
            failed += 1
    except Exception as e:
        print(f"❌ FAILED: {test['name']}")
        print(f"   Unexpected error: {e}")
        failed += 1

print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'='*60}")
