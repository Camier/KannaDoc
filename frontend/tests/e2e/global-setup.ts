import { FullConfig } from '@playwright/test';

/**
 * Global E2E Test Setup
 *
 * Runs before all tests. Use for:
 * - Setting up test databases
 * - Seeding test data
 * - Global configuration
 */
async function globalSetup(config: FullConfig) {
  console.log('Starting E2E test suite...');

  // You can add global setup logic here:
  // - Start test backend server
  // - Seed database with test data
  // - Configure test environment variables

  console.log(`Base URL: ${config.projects?.[0]?.use?.baseURL || 'http://localhost:8090'}`);
  console.log('E2E test setup complete.');
}

export default globalSetup;
