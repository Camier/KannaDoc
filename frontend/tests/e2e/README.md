# E2E Tests with Playwright

This directory contains end-to-end tests for the Layra application using Playwright.

## Setup

Playwright is already installed. Browsers are installed in `~/.cache/ms-playwright/`.

## Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui

# Run in debug mode
npm run test:e2e:debug

# Run specific test file
npx playwright test auth.spec.ts

# Run specific test
npx playwright test -g "user can login"

# Run in specific browser
npx playwright test --project=chromium

# View test report
npm run test:e2e:report
```

## Test Structure

```
tests/e2e/
├── auth.spec.ts           # Authentication flow tests
├── chat.spec.ts           # AI chat functionality tests
├── knowledge-base.spec.ts # Knowledge base management tests
├── test-helpers.ts        # Reusable test utilities
├── global-setup.ts        # Global test setup
└── global-teardown.ts     # Global test teardown
```

## Writing New Tests

1. Create a new `.spec.ts` file in this directory
2. Import test utilities from `./test-helpers.ts`
3. Use `test.describe()` to group related tests
4. Use `test.beforeEach()` for common setup
5. Use `expect()` for assertions

```typescript
import { test, expect } from '@playwright/test';
import { login, credentials } from './test-helpers';

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    const user = credentials.generateUser();
    await login(page, user.name, user.password);
  });

  test('does something', async ({ page }) => {
    await page.goto('/my-page');
    await expect(page.locator('h1')).toHaveText('My Page');
  });
});
```

## Test Data

Tests use unique usernames with timestamps to avoid conflicts:
- Format: `e2e_test_${timestamp}_${random}`

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Install dependencies
  run: npm ci

- name: Install Playwright browsers
  run: npx playwright install --with-deps

- name: Run E2E tests
  run: npm run test:e2e

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: test-results/
```

## Troubleshooting

**Tests fail with "connection refused"**
- Ensure the dev server is running on port 8090
- Or update `baseURL` in `playwright.config.ts`

**Tests timeout**
- Increase timeout in `playwright.config.ts`
- Check if backend is responsive

**Browser not found**
- Run `npx playwright install chromium`
