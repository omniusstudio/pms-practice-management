import { test, expect } from '@playwright/test';

test.describe('Authentication Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
  });

  test('should display login page for unauthenticated users', async ({ page }) => {
    // Verify login page elements
    await expect(page.locator('h1')).toContainText('Sign In');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show validation errors for invalid login', async ({ page }) => {
    // Try to submit empty form
    await page.click('button[type="submit"]');

    // Check for validation messages
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Fill in invalid credentials
    await page.fill('input[type="email"]', 'invalid@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message (no PHI exposed)
    await expect(page.locator('text=Invalid credentials')).toBeVisible();

    // Should not expose any sensitive information
    await expect(page.locator('text=user not found')).not.toBeVisible();
    await expect(page.locator('text=password incorrect')).not.toBeVisible();
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    // Use test credentials (these should be configured in test environment)
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'testpassword123');
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('should handle session timeout gracefully', async ({ page }) => {
    // Login first
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'testpassword123');
    await page.click('button[type="submit"]');

    // Wait for dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);

    // Simulate session expiration by clearing storage
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Try to access a protected resource
    await page.goto('/patients');

    // Should redirect to login
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.locator('text=Session expired')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'testpassword123');
    await page.click('button[type="submit"]');

    // Wait for dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);

    // Click logout
    await page.click('[data-testid="logout-button"]');

    // Should redirect to login page
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.locator('h1')).toContainText('Sign In');

    // Should not be able to access protected routes
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*\/login/);
  });
});
