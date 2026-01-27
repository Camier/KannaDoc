import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Knowledge Base Management
 *
 * Tests:
 * - Create knowledge base
 * - List knowledge bases
 * - Delete knowledge base
 * - Rename knowledge base
 * - Upload files to knowledge base
 * - Search/filter knowledge bases
 */

const testUser = {
  name: `e2e_kb_${Date.now()}`,
  email: `e2e_kb_${Date.now()}@example.com`,
  password: 'TestPassword123!',
};

test.describe('Knowledge Base Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/sign-in');
    await page.fill('input[name="name"]', testUser.name);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Wait for successful login
    await page.waitForURL(/\/(en|zh)?$/, { timeout: 5000 });

    // Navigate to knowledge base page
    await page.goto('/knowledge-base');
    await expect(page).toHaveURL(/.*knowledge-base/);
  });

  test('should display knowledge base page', async ({ page }) => {
    // Check for key elements
    await expect(page.locator('text=/knowledge|base/i')).toBeVisible();
  });

  test('can open create knowledge base modal', async ({ page }) => {
    // Look for create button (could be icon or text)
    const createButton = page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first();
    await createButton.click();

    // Modal should appear
    await expect(page.locator('text=/create|new.*knowledge/i')).toBeVisible({ timeout: 3000 });
  });

  test('can create a new knowledge base', async ({ page }) => {
    const kbName = `Test KB ${Date.now()}`;

    // Open create modal
    const createButton = page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first();
    await createButton.click();

    // Fill in knowledge base name
    const nameInput = page.locator('input[type="text"]').first();
    await nameInput.fill(kbName);

    // Submit form
    const confirmButton = page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first();
    await confirmButton.click();

    // Wait for creation and verify it appears in the list
    await page.waitForTimeout(1000);
    await expect(page.getByText(kbName)).toBeVisible({ timeout: 5000 });
  });

  test('should show error for empty knowledge base name', async ({ page }) => {
    // Open create modal
    const createButton = page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first();
    await createButton.click();

    // Try to submit without name
    const confirmButton = page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first();
    await confirmButton.click();

    // Should show validation error
    await expect(page.locator('text=/required|empty|error/i')).toBeVisible({ timeout: 3000 });
  });

  test('should show error for duplicate knowledge base name', async ({ page }) => {
    const kbName = `Duplicate KB ${Date.now()}`;

    // Create first knowledge base
    await page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first().click();
    await page.locator('input[type="text"]').first().fill(kbName);
    await page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first().click();
    await page.waitForTimeout(1000);

    // Try to create duplicate
    await page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first().click();
    await page.locator('input[type="text"]').first().fill(kbName);
    await page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first().click();

    // Should show duplicate error
    await expect(page.locator('text=/duplicate|exists/i')).toBeVisible({ timeout: 3000 });
  });

  test('can select a knowledge base', async ({ page }) => {
    // Create a knowledge base first
    const kbName = `Selectable KB ${Date.now()}`;
    await page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first().click();
    await page.locator('input[type="text"]').first().fill(kbName);
    await page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first().click();
    await page.waitForTimeout(1000);

    // Click on the knowledge base
    await page.getByText(kbName).click();

    // Should show details or upload interface
    await expect(page.locator('text=/upload|file|detail/i')).toBeVisible({ timeout: 3000 });
  });

  test('can rename a knowledge base', async ({ page }) => {
    const oldName = `Old Name ${Date.now()}`;
    const newName = `New Name ${Date.now()}`;

    // Create a knowledge base
    await page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first().click();
    await page.locator('input[type="text"]').first().fill(oldName);
    await page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first().click();
    await page.waitForTimeout(1000);

    // Right-click or find rename option
    const kbElement = page.getByText(oldName);
    await kbElement.click();
    await page.keyboard.press('Shift+F10'); // Context menu

    // Or look for edit/rename button
    const renameButton = page.getByRole('button').filter({ hasText: /rename|edit/i }).first();
    if (await renameButton.isVisible()) {
      await renameButton.click();
    } else {
      // Try inline editing
      await kbElement.dblclick();
    }

    // Type new name and confirm
    const nameInput = page.locator('input[type="text"]').first();
    await nameInput.fill(newName);
    await page.keyboard.press('Enter');

    // Verify renamed
    await expect(page.getByText(newName)).toBeVisible({ timeout: 3000 });
    await expect(page.getByText(oldName)).not.toBeVisible();
  });

  test('can delete a knowledge base', async ({ page }) => {
    const kbName = `Delete Me ${Date.now()}`;

    // Create a knowledge base
    await page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first().click();
    await page.locator('input[type="text"]').first().fill(kbName);
    await page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first().click();
    await page.waitForTimeout(1000);

    // Select the knowledge base
    await page.getByText(kbName).click();

    // Find and click delete button
    const deleteButton = page.getByRole('button').filter({ hasText: /delete|remove/i }).first();
    await deleteButton.click();

    // Confirm deletion if modal appears
    const confirmButton = page.getByRole('button').filter({ hasText: /confirm|delete|yes/i });
    if (await confirmButton.first().isVisible()) {
      await confirmButton.first().click();
    }

    // Verify deleted
    await expect(page.getByText(kbName)).not.toBeVisible({ timeout: 3000 });
  });

  test('can search knowledge bases', async ({ page }) => {
    const searchTerm = 'test';

    // Create multiple knowledge bases
    for (let i = 0; i < 3; i++) {
      await page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first().click();
      await page.locator('input[type="text"]').first().fill(`${searchTerm} KB ${i}`);
      await page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first().click();
      await page.waitForTimeout(500);
    }

    // Use search input
    const searchInput = page.locator('input[placeholder*="search" i], input[type="search"]').first();
    await searchInput.fill(searchTerm);

    // Should show filtered results
    await expect(page.locator(`text=/${searchTerm}/i`).first()).toBeVisible({ timeout: 3000 });
  });

  test('can navigate to AI chat from knowledge base', async ({ page }) => {
    // Navigate to AI chat page
    await page.goto('/ai-chat');

    // Verify navigation
    await expect(page).toHaveURL(/.*ai-chat/);
    await expect(page.locator('text=/chat|message|conversation/i')).toBeVisible();
  });
});
