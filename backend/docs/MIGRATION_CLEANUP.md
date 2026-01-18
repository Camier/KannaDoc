# Password Migration Cleanup

## When to Clean Up

Run `python scripts/check_migration_status.py`. When it reports 0 legacy users, you can clean up.

## Cleanup Steps

### 1. Remove Legacy Function

Delete `verify_password_legacy()` from `app/core/security.py`.

### 2. Simplify authenticate_user

Remove the legacy migration path from `authenticate_user()`:

```python
async def authenticate_user(db: AsyncSession, username: str, password: str):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if user and verify_password(password, user.hashed_password):
        return user
    return None
```

### 3. Remove Migration Flag (Optional)

After verifying all users are migrated:

Create Alembic migration:

```python
# backend/migrations/versions/YYYYMMDD_remove_password_migration_flag.py
def upgrade():
    op.drop_column('users', 'password_migration_required')

def downgrade():
    op.add_column('users', sa.Column('password_migration_required', sa.Boolean(), nullable=False, server_default='0')
```

### 4. Remove Documentation

Delete `PASSWORD_MIGRATION.md` and this file.

## Verification

After cleanup, run full test suite:

```bash
pytest tests/ -v --cov=app
```

All tests should pass.
