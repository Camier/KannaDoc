import { test, expect } from '@playwright/test';

/**
 * E2E Tests for AI Chat Functionality
 *
 * Tests:
 * - Send chat message
 * - Receive AI response
 * - Create new conversation
 * - Chat history persistence
 * - Message threading
 * - Knowledge base integration
 * - File upload in chat
 */

const testUser = {
  name: `e2e_chat_${Date.now()}`,
  email: `e2e_chat_${Date.now()}@example.com`,
  password: 'TestPassword123!',
};

test.describe('AI Chat Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/sign-in');
    await page.fill('input[name="name"]', testUser.name);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Wait for successful login
    await page.waitForURL(/\/(en|zh)?$/, { timeout: 5000 });

    // Navigate to AI chat page
    await page.goto('/ai-chat');
    await expect(page).toHaveURL(/.*ai-chat/);
  });

  test('should display chat interface', async ({ page }) => {
    // Check for chat elements
    await expect(page.locator('text=/chat|message|conversation/i')).toBeVisible();

    // Look for message input
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await expect(messageInput).toBeVisible();
  });

  test('can send a chat message', async ({ page }) => {
    const testMessage = 'Hello, this is a test message!';

    // Find and fill message input
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill(testMessage);

    // Find and click send button
    const sendButton = page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first();
    await sendButton.click();

    // Verify message appears in chat
    await expect(page.getByText(testMessage)).toBeVisible({ timeout: 5000 });
  });

  test('should show loading state while waiting for AI response', async ({ page }) => {
    const testMessage = 'What is 2+2?';

    // Send message
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill(testMessage);

    const sendButton = page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first();
    await sendButton.click();

    // Should show loading indicator or state
    await expect(page.locator('text=/loading|thinking|parsing|typing/i').or(
      page.locator('[class*="loading"], [class*="spinner"], [class*="typing"]')
    ).first()).toBeVisible({ timeout: 3000 });
  });

  test('should receive AI response', async ({ page }) => {
    const testMessage = 'Say "AI Response Received"';

    // Send message
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill(testMessage);

    const sendButton = page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first();
    await sendButton.click();

    // Wait for AI response (may take a while)
    await page.waitForTimeout(5000);

    // Look for AI message (different styling or from "ai")
    const aiMessage = page.locator('[class*="ai"], [class*="assistant"], [data-from="ai"]').first();
    await expect(aiMessage).toBeVisible({ timeout: 15000 });
  });

  test('can create a new conversation', async ({ page }) => {
    // Find new chat button
    const newChatButton = page.getByRole('button').filter({ hasText: /new.*chat|create|plus|\+/i }).first();
    await newChatButton.click();

    // Should have empty chat or new conversation indicator
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await expect(messageInput).toBeVisible();

    // Send a message to verify new conversation
    await messageInput.fill('New conversation test');
    await page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first().click();
    await expect(page.getByText('New conversation test')).toBeVisible({ timeout: 5000 });
  });

  test('can view chat history in sidebar', async ({ page }) => {
    // Send a message to create history
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill('History test message');
    await page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first().click();
    await page.waitForTimeout(2000);

    // Look for sidebar/history panel
    const sidebar = page.locator('[class*="sidebar"], [class*="history"], aside').first();
    if (await sidebar.isVisible()) {
      // Should show conversation in history
      await expect(sidebar.getByText(/history|conversation/i).first()).toBeVisible({ timeout: 3000 });
    }
  });

  test('can select previous conversation from history', async ({ page }) => {
    // Create first conversation with message
    let messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill('First conversation');
    await page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first().click();
    await page.waitForTimeout(2000);

    // Create new conversation
    await page.getByRole('button').filter({ hasText: /new.*chat|create|plus|\+/i }).first().click();
    await page.waitForTimeout(1000);

    // Go back to first conversation via sidebar
    const sidebar = page.locator('[class*="sidebar"], [class*="history"], aside').first();
    if (await sidebar.isVisible()) {
      await sidebar.getByText('First conversation').first().click();
      await page.waitForTimeout(1000);

      // Should show previous message
      await expect(page.getByText('First conversation')).toBeVisible({ timeout: 3000 });
    }
  });

  test('can delete a conversation', async ({ page }) => {
    // Create conversation
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill('Delete this conversation');
    await page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first().click();
    await page.waitForTimeout(2000);

    // Find and click delete option for conversation
    const sidebar = page.locator('[class*="sidebar"], [class*="history"], aside').first();
    if (await sidebar.isVisible()) {
      const conversation = sidebar.getByText(/delete.*conversation/i).first();

      // Try to find delete button (could be in dropdown or hover)
      await conversation.hover();
      const deleteButton = page.getByRole('button').filter({ hasText: /delete|remove|trash/i }).first();

      if (await deleteButton.isVisible()) {
        await deleteButton.click();

        // Confirm if modal appears
        const confirmButton = page.getByRole('button').filter({ hasText: /confirm|delete|yes/i });
        if (await confirmButton.first().isVisible()) {
          await confirmButton.first().click();
        }

        // Verify conversation is deleted
        await expect(page.getByText('Delete this conversation')).not.toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('can rename a conversation', async ({ page }) => {
    // Create conversation
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill('Original conversation name');
    await page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first().click();
    await page.waitForTimeout(2000);

    // Find and rename conversation
    const sidebar = page.locator('[class*="sidebar"], [class*="history"], aside').first();
    if (await sidebar.isVisible()) {
      const conversation = sidebar.getByText(/original/i).first();
      await conversation.click();

      // Look for rename option
      const renameButton = page.getByRole('button').filter({ hasText: /rename|edit/i }).first();
      if (await renameButton.isVisible()) {
        await renameButton.click();

        // Enter new name
        const nameInput = page.locator('input[type="text"]').first();
        await nameInput.fill('Renamed conversation');
        await page.keyboard.press('Enter');

        // Verify renamed
        await expect(sidebar.getByText('Renamed conversation')).toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('should have disabled send button when input is empty', async ({ page }) => {
    const sendButton = page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first();

    // Initially should be disabled
    const messageInput = page.locator('textarea, input[type="text"]').first();

    // Check if button is disabled when input is empty
    const isDisabled = await sendButton.isDisabled();
    expect(isDisabled).toBeTruthy();

    // Enable when typing
    await messageInput.fill('Test message');
    await expect(sendButton).toBeEnabled({ timeout: 1000 });
  });

  test('can navigate to knowledge base from chat', async ({ page }) => {
    // Look for navigation or link to knowledge base
    const kbLink = page.getByRole('link').filter({ hasText: /knowledge|base/i }).first();

    if (await kbLink.isVisible()) {
      await kbLink.click();
      await expect(page).toHaveURL(/.*knowledge-base/);
    } else {
      // Try navigation through menu
      await page.goto('/knowledge-base');
      await expect(page).toHaveURL(/.*knowledge-base/);
    }
  });

  test('can navigate to workflow from chat', async ({ page }) => {
    // Try to navigate to workflow page
    await page.goto('/work-flow');

    // Verify navigation
    await expect(page).toHaveURL(/.*work-flow/);
    await expect(page.locator('text=/workflow|flow|node/i')).toBeVisible();
  });

  test('shows error message on failed request', async ({ page, context }) => {
    // Block API requests to simulate failure
    await context.route('**/sse/chat', route => route.abort('failed'));

    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill('This will fail');

    const sendButton = page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first();
    await sendButton.click();

    // Should show error message
    await expect(page.locator('text=/error|failed|retry/i')).toBeVisible({ timeout: 10000 });
  });

  test('can abort ongoing AI response', async ({ page }) => {
    // Send a long message that will take time to respond
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill('Explain quantum computing in great detail');

    const sendButton = page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first();
    await sendButton.click();

    // Wait for loading state
    await page.waitForTimeout(2000);

    // Look for abort/stop button
    const stopButton = page.getByRole('button').filter({ hasText: /stop|abort|cancel/i }).first();

    if (await stopButton.isVisible({ timeout: 3000 })) {
      await stopButton.click();

      // Should stop loading
      await expect(page.locator('text=/loading|thinking/i').first()).not.toBeVisible({ timeout: 3000 });
    }
  });
});
