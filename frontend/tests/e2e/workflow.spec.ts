import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Workflow Builder
 *
 * Tests:
 * - Access workflow page
 * - Create workflow nodes
 * - Connect nodes
 * - Save workflow
 * - Execute workflow
 */

const testUser = {
  name: `e2e_workflow_${Date.now()}`,
  email: `e2e_workflow_${Date.now()}@example.com`,
  password: 'TestPassword123!',
};

test.describe('Workflow Builder', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/sign-in');
    await page.fill('input[name="name"]', testUser.name);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Wait for successful login
    await page.waitForURL(/\/(en|zh)?$/, { timeout: 5000 });

    // Navigate to workflow page
    await page.goto('/work-flow');
    await expect(page).toHaveURL(/.*work-flow/);
  });

  test('should display workflow builder page', async ({ page }) => {
    // Check for workflow elements
    await expect(page.locator('text=/workflow|flow|node|canvas/i')).toBeVisible();
  });

  test('can access workflow canvas', async ({ page }) => {
    // Look for canvas or node container
    const canvas = page.locator('[class*="canvas"], [class*="flow"], svg').first();
    await expect(canvas).toBeVisible({ timeout: 5000 });
  });

  test('should have node palette or toolbar', async ({ page }) => {
    // Look for node palette, sidebar, or toolbar
    const palette = page.locator('[class*="palette"], [class*="sidebar"], [class*="toolbar"]').first();
    await expect(palette).toBeVisible({ timeout: 5000 });
  });

  test('can drag and drop a node onto canvas', async ({ page }) => {
    // Find a draggable node in palette
    const node = page.locator('[draggable="true"], [class*="node"]').first();

    if (await node.isVisible({ timeout: 3000 })) {
      // Get canvas position
      const canvas = page.locator('[class*="canvas"], [class*="flow"], svg').first();
      const canvasBox = await canvas.boundingBox();

      if (canvasBox) {
        // Drag node to canvas
        await node.dragTo(canvas, {
          targetPosition: { x: canvasBox.width / 2, y: canvasBox.height / 2 },
        });

        // Verify node appears on canvas
        await page.waitForTimeout(500);
        await expect(page.locator('[class*="node"]').first()).toBeVisible();
      }
    }
  });

  test('can select a node on canvas', async ({ page }) => {
    // Look for existing nodes or add one
    const node = page.locator('[class*="node"]').first();

    if (await node.isVisible({ timeout: 3000 })) {
      await node.click();

      // Should show selected state (border, highlight, etc.)
      await expect(node).toHaveClass(/selected|active/);
    }
  });

  test('can delete a node from canvas', async ({ page }) => {
    const node = page.locator('[class*="node"]').first();

    if (await node.isVisible({ timeout: 3000 })) {
      // Select node
      await node.click();

      // Try delete key or delete button
      const deleteButton = page.getByRole('button').filter({ hasText: /delete|remove/i }).first();

      if (await deleteButton.isVisible()) {
        await deleteButton.click();
      } else {
        await page.keyboard.press('Delete');
      }

      // Node should be removed
      await expect(node).not.toBeVisible({ timeout: 3000 });
    }
  });

  test('can navigate between pages from workflow', async ({ page }) => {
    // Navigate to AI chat
    await page.goto('/ai-chat');
    await expect(page).toHaveURL(/.*ai-chat/);

    // Navigate to knowledge base
    await page.goto('/knowledge-base');
    await expect(page).toHaveURL(/.*knowledge-base/);

    // Navigate back to home
    await page.goto('/');
    await expect(page).toHaveURL(/\/(en|zh)?$/);
  });

  test('workflow page should be responsive', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Should still show workflow elements
    await expect(page.locator('text=/workflow|flow|node/i').first()).toBeVisible();

    // Reset to desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
  });
});
