import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Authentication Flow
 *
 * Tests:
 * - User registration
 * - User login
 * - Logout functionality
 * - Protected route access
 * - Form validation (illegal characters)
 */

test.describe('Authentication Flow', () => {
  const testUser = {
    name: `e2e_test_${Date.now()}`,
    email: `e2e_test_${Date.now()}@example.com`,
    password: 'TestPassword123!',
  };

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display sign-in page when not authenticated', async ({ page }) => {
    await page.goto('/');
    // Should redirect to sign-in or show join button
    const joinButton = page.getByRole('button', { name: /join|start/i });
    await expect(joinButton).toBeVisible();
  });

  test('user can navigate to sign-in page', async ({ page }) => {
    await page.goto('/');
    await page.click('text=/join|start/i');
    await expect(page).toHaveURL(/.*sign-in/);
  });

  test('should show validation error for illegal characters in username', async ({ page }) => {
    await page.goto('/sign-in');

    // Switch to register mode
    await page.click('text=.*Sign Up.*');

    // Fill form with illegal characters
    await page.fill('input[name="name"]', 'test-user');
    await page.fill('input[name="email"]', testUser.email);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Should show error about illegal characters
    await expect(page.locator('text=/illegal|error/i')).toBeVisible({ timeout: 5000 });
  });

  test('should show validation error for empty username', async ({ page }) => {
    await page.goto('/sign-in');
    await page.click('text=.*Sign Up.*');

    // Try to submit with empty name
    await page.fill('input[name="name"]', '');
    await page.fill('input[name="email"]', testUser.email);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // HTML5 validation should prevent submission
    const nameInput = page.locator('input[name="name"]');
    await expect(nameInput).toHaveAttribute('required', '');
  });

  test('user can register a new account', async ({ page }) => {
    await page.goto('/sign-in');

    // Switch to register mode if in login mode
    const signUpButton = page.getByText(/sign.*up/i);
    if (await signUpButton.isVisible()) {
      await signUpButton.click();
    }

    // Fill registration form
    await page.fill('input[name="name"]', testUser.name);
    await page.fill('input[name="email"]', testUser.email);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Should redirect to home or show success
    await expect(page).toHaveURL(/\/(en|zh)?$/);
  });

  test('user can login with valid credentials', async ({ page }) => {
    await page.goto('/sign-in');

    // Fill login form
    await page.fill('input[name="name"]', testUser.name);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Should redirect to home page
    await expect(page).toHaveURL(/\/(en|zh)?$/);

    // Should show navigation options
    const startButton = page.getByRole('button', { name: /start/i });
    await expect(startButton).toBeVisible({ timeout: 5000 });
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/sign-in');

    await page.fill('input[name="name"]', 'nonexistentuser');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=/failed|error|incorrect/i')).toBeVisible({ timeout: 5000 });
  });

  test('can toggle between login and register modes', async ({ page }) => {
    await page.goto('/sign-in');

    // Should be in login mode by default
    await expect(page.getByText(/login|sign.*in/i)).toBeVisible();
    await expect(page.locator('input[name="email"]')).not.toBeVisible();

    // Switch to register mode
    await page.click('text=.*Sign Up.*');
    await expect(page.locator('input[name="email"]')).toBeVisible();

    // Switch back to login mode
    await page.click('text=.*Sign In.*');
    await expect(page.locator('input[name="email"]')).not.toBeVisible();
  });

  test('authenticated user can access protected routes', async ({ page }) => {
    // First login
    await page.goto('/sign-in');
    await page.fill('input[name="name"]', testUser.name);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Wait for redirect
    await page.waitForURL(/\/(en|zh)?$/);

    // Try to access AI Chat page
    await page.goto('/ai-chat');
    await expect(page).toHaveURL(/.*ai-chat/);
    await expect(page.locator('text=/chat|message/i')).toBeVisible();
  });

  test('unauthenticated user is redirected from protected routes', async ({ page, context }) => {
    // Clear any existing auth tokens
    await context.clearCookies();

    // Try to access protected route directly
    await page.goto('/ai-chat');

    // Should redirect to sign-in
    await expect(page).toHaveURL(/.*sign-in/);
  });
});
