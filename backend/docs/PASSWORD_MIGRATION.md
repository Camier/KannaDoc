# Password Migration Documentation

## Overview

This system previously used a **hardcoded password salt** (`"mynameisliwei,nicetomeetyou!"`) combined with bcrypt hashing. This was a **critical security vulnerability** that has been fixed.

## What Changed

### Before (Insecure)
```python
salt = "mynameisliwei,nicetomeetyou!"
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password + salt, hashed_password)
```

### After (Secure)
```python
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
```

Bcrypt now handles salting automatically with a **unique random salt per password**.

## Migration Strategy

### Automatic Migration on Login

Existing user passwords are automatically migrated on their next successful login:

1. User logs in with their existing credentials
2. System verifies using legacy method (with old salt)
3. If successful, password is rehashed using proper bcrypt
4. `password_migration_required` flag is set to `False`
5. Database is updated

### New Users

New user registrations automatically use the secure hashing method and have `password_migration_required = False`.

## Database Schema

```sql
ALTER TABLE users ADD COLUMN password_migration_required BOOLEAN DEFAULT TRUE;
```

## Verification

To verify migration is complete:

```sql
SELECT COUNT(*) FROM users WHERE password_migration_required = TRUE;
```

When this returns 0, all users have been migrated.

## Timeline

- **Deployment**: Users with `password_migration_required = TRUE` can still log in
- **Migration Window**: Allow 2-4 weeks for all active users to log in
- **Cleanup**: After migration window, consider forcing password reset for any remaining legacy users

## Security Advisory

If you believe the database has been compromised, **force password reset for all users** immediately:

```sql
UPDATE users SET password_migration_required = TRUE, hashed_password = 'RESET_REQUIRED';
```

Then implement a password reset flow.
