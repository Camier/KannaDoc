import { Page, BrowserContext } from '@playwright/test';

/**
 * E2E Test Helper Functions
 *
 * Reusable utilities for authentication, navigation, and common actions
 */

export const credentials = {
  // Test user credentials - use unique usernames per test run to avoid conflicts
  generateUser: () => ({
    name: `e2e_test_${Date.now()}_${Math.random().toString(36).substring(7)}`,
    email: `e2e_test_${Date.now()}@example.com`,
    password: 'TestPassword123!',
  }),
};

/**
 * Perform login with given credentials
 */
export async function login(page: Page, username: string, password: string) {
  await page.goto('/sign-in');
  await page.fill('input[name="name"]', username);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');

  // Wait for navigation after login
  await page.waitForURL(/\/(en|zh)?$/, { timeout: 5000 });
}

/**
 * Register a new user
 */
export async function register(page: Page, name: string, email: string, password: string) {
  await page.goto('/sign-in');

  // Switch to register mode
  const signUpButton = page.getByText(/sign.*up/i);
  if (await signUpButton.isVisible()) {
    await signUpButton.click();
  }

  // Fill form
  await page.fill('input[name="name"]', name);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');

  // Wait for redirect
  await page.waitForURL(/\/(en|zh)?$/, { timeout: 5000 });
}

/**
 * Clear authentication (logout)
 */
export async function clearAuth(context: BrowserContext) {
  await context.clearCookies();
  await context.clearPermissions();
}

/**
 * Create a knowledge base
 */
export async function createKnowledgeBase(page: Page, name: string) {
  // Open create modal
  const createButton = page.getByRole('button').filter({ hasText: /create|add|new|\+/i }).first();
  await createButton.click();

  // Fill name
  const nameInput = page.locator('input[type="text"]').first();
  await nameInput.fill(name);

  // Submit
  const confirmButton = page.getByRole('button').filter({ hasText: /confirm|create|submit/i }).first();
  await confirmButton.click();

  // Wait for creation
  await page.waitForTimeout(1000);
}

/**
 * Send a chat message
 */
export async function sendChatMessage(page: Page, message: string) {
  const messageInput = page.locator('textarea, input[type="text"]').first();
  await messageInput.fill(message);

  const sendButton = page.getByRole('button').filter({ hasText: /send|submit|arrow/i }).first();
  await sendButton.click();

  // Wait for message to appear
  await page.waitForTimeout(500);
}

/**
 * Wait for AI response
 */
export async function waitForAIResponse(page: Page, timeout = 15000) {
  await page.waitForSelector('[class*="ai"], [class*="assistant"], [data-from="ai"]', {
    timeout,
  });
}

/**
 * Navigate to a specific route
 */
export async function navigateTo(page: Page, route: string) {
  await page.goto(route);
  await page.waitForLoadState('networkidle');
}

/**
 * Take screenshot on failure
 */
export async function captureScreenshot(page: Page, name: string) {
  await page.screenshot({
    path: `test-results/screenshots/${name}.png`,
    fullPage: true,
  });
}

/**
 * Wait for modal to appear and close it
 */
export async function closeModal(page: Page) {
  const closeButton = page.getByRole('button').filter({ hasText: /close|cancel|×/i }).first();
  if (await closeButton.isVisible()) {
    await closeButton.click();
  }
}

/**
 * Get visible text from selector
 */
export async function getText(page: Page, selector: string): Promise<string> {
  const element = page.locator(selector).first();
  return await element.textContent() || '';
}

/**
 * Wait for element to be visible
 */
export async function waitForVisible(page: Page, selector: string, timeout = 5000) {
  await page.waitForSelector(selector, { state: 'visible', timeout });
}

/**
 * Wait for element to be hidden
 */
export async function waitForHidden(page: Page, selector: string, timeout = 5000) {
  await page.waitForSelector(selector, { state: 'hidden', timeout });
}

/**
 * Check if element exists
 */
export async function exists(page: Page, selector: string): Promise<boolean> {
  return await page.locator(selector).count() > 0;
}

/**
 * Mock API route for testing
 */
export function mockAPI(context: BrowserContext, pattern: string, response: any) {
  context.route(pattern, route => {
    route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(response),
    });
  });
}

/**
 * Fail API route for error testing
 */
export function failAPI(context: BrowserContext, pattern: string, status = 500) {
  context.route(pattern, route => {
    route.abort('failed');
  });
}

/**
 * Retry function with timeout
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: { retries?: number; delay?: number } = {}
): Promise<T> {
  const { retries = 3, delay = 1000 } = options;

  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw new Error('Retry failed');
}

/**
 * Wait for network idle
 */
export async function waitForNetworkIdle(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}
