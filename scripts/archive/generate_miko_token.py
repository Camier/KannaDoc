import asyncio
import os
import sys
from datetime import timedelta

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.security import create_access_token, store_token
from app.core.config import settings


async def main():
    username = "miko"
    expires_delta = timedelta(hours=24)

    # Create access token
    access_token = create_access_token(
        data={"sub": username}, expires_delta=expires_delta
    )

    # Store in Redis
    await store_token(
        token=access_token,
        username=username,
        expires_in_seconds=int(expires_delta.total_seconds()),
    )

    print(access_token)


if __name__ == "__main__":
    asyncio.run(main())
