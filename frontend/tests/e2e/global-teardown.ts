import { FullConfig } from '@playwright/test';

/**
 * Global E2E Test Teardown
 *
 * Runs after all tests complete. Use for:
 * - Cleaning up test data
 * - Stopping test servers
 * - Generating reports
 */
async function globalTeardown(config: FullConfig) {
  console.log('E2E test suite completed.');

  // You can add cleanup logic here:
  // - Delete test users/data
  // - Stop test servers
  // - Archive test results

  console.log('Cleanup complete.');
}

export default globalTeardown;
