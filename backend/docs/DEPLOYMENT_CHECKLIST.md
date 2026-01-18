# Password Migration Deployment Checklist

## Pre-Deployment

- [ ] All tests passing: `pytest tests/ -v`
- [ ] Migration status baseline recorded
- [ ] Database backed up
- [ ] Rollback plan documented

## Deployment Steps

1. [ ] Deploy code with new authentication logic
2. [ ] Run Alembic migration: `alembic upgrade head`
3. [ ] Verify new registrations work correctly
4. [ ] Test login with existing user account
5. [ ] Monitor application logs for errors

## Post-Deployment

- [ ] Check migration status daily: `python scripts/check_migration_status.py`
- [ ] Monitor error rates in authentication endpoints
- [ ] Track user complaints about login issues
- [ ] Plan cleanup after 90% migration

## Rollback Plan

If critical issues occur:

1. Revert code to previous version
2. Database is compatible with old code (flag is additive)
3. No data loss occurs

## Monitoring Commands

```bash
# Check migration status
python scripts/check_migration_status.py

# Check recent logins
tail -f /var/log/layra/app.log | grep "login"

# Monitor authentication errors
tail -f /var/log/layra/app.log | grep "ERROR.*auth"
```
