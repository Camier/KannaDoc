#!/usr/bin/env python3
"""Script to check password migration status"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings
from app.models.user import User


async def main():
    """Check how many users still need migration"""
    engine = create_async_engine(settings.db_url)

    async with engine.begin() as conn:
        result = await conn.execute(
            select(func.count(User.id)).where(User.password_migration_required == True)
        )
        legacy_count = result.scalar()

        result = await conn.execute(select(func.count(User.id)))
        total_count = result.scalar()

    await engine.dispose()

    percentage = (legacy_count / total_count * 100) if total_count > 0 else 0

    print(f"Password Migration Status:")
    print(f"  Total users: {total_count}")
    print(f"  Legacy users: {legacy_count}")
    print(f"  Migrated: {total_count - legacy_count} ({100 - percentage:.1f}%)")
    print(f"  Remaining: {legacy_count} ({percentage:.1f}%)")

    if legacy_count == 0:
        print("\n✅ Migration complete! You can now remove verify_password_legacy()")
    elif percentage < 5:
        print(f"\n⚠️  Almost complete! {legacy_count} users still need to log in.")
    else:
        print(f"\n🔄 Migration in progress. {percentage:.1f}% of users still need to log in.")


if __name__ == "__main__":
    asyncio.run(main())
