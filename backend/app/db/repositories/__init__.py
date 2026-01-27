"""
MongoDB Repository Pattern - NOT IMPLEMENTED

This repository pattern migration was started but NOT completed.

STATUS: The repository files were deleted and the migration was rolled back.
All endpoints continue to use the legacy MongoDB class directly from app.db.mongo

DO NOT USE: The imports below are broken and will cause ImportError.

Current Data Access Pattern:
    from app.db.mongo import get_mongo

    async def endpoint(db: MongoDB = Depends(get_mongo)):
        return await db.get_something(...)

Migration History:
- 2026-01-26: Repository files deleted (see git status: backend/app/db/repositories/*.py)
- Migration was rolled back due to incomplete implementation
- All 20+ endpoints use legacy MongoDB class directly

To Complete Repository Migration:
1. Decide whether to implement repository pattern or remove this directory
2. If implementing: Restore/create repository files, update all 20+ endpoints
3. If removing: Delete this __init__.py file and repositories directory

See docs/plans/2026-01-28-codebase-remediation.md for context.
"""
