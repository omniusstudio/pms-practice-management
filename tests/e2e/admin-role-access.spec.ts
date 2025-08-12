import { test, expect } from "@playwright/test";

// Test users with different roles
const TEST_USERS = {
  admin: {
    email: "admin@test.com",
    password: "adminpass123",
    roles: ["admin"],
  },
  clinician: {
    email: "clinician@test.com",
    password: "clinicianpass123",
    roles: ["clinician"],
  },
  frontDesk: {
    email: "frontdesk@test.com",
    password: "frontdeskpass123",
    roles: ["front_desk"],
  },
  biller: {
    email: "biller@test.com",
    password: "billerpass123",
    roles: ["biller"],
  },
} as const;

// Helper function to simulate user authentication with roles
async function loginWithRoles(page: any, userRoles: string[]) {
  // Create mock user data
  const mockUser = {
    id: `test-user-${Date.now()}`,
    email: "test@example.com",
    name: "Test User",
    roles: userRoles,
    provider: "auth0",
  };

  // Set authentication state in localStorage
  await page.addInitScript((userData) => {
    // Set token
    localStorage.setItem("pms_auth_token", "mock-jwt-token");
    localStorage.setItem("pms_auth_token_expiry", (Date.now() + 30 * 60 * 1000).toString());

    // Set user data
    localStorage.setItem("pms_user_data", JSON.stringify(userData));
  }, mockUser);

  // Mock the API responses for authentication
  await page.route("**/api/auth/user", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockUser),
    });
  });

  await page.goto("/");
}

test.describe("Admin Role Access Control", () => {
  test.beforeEach(async ({ page }) => {
    // Mock feature flags API
    await page.route("**/api/feature-flags", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            adminRouteEnabled: true,
            billingEnabled: true,
            appointmentsEnabled: true,
            dashboardEnabled: true,
          },
        }),
      });
    });
  });

  test("admin user can access admin page", async ({ page }) => {
    await loginWithRoles(page, ["admin"]);

    // Navigate to admin page
    await page.goto("/admin");

    // Should be able to access admin page
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible();
    await expect(page.locator("h1")).toContainText("Admin Dashboard");
  });

  test("admin user can see admin navigation item", async ({ page }) => {
    await loginWithRoles(page, ["admin"]);

    await page.goto("/dashboard");

    // Should see admin link in navigation
    await expect(page.locator('nav a[href="/admin"]')).toBeVisible();
    await expect(page.locator('nav a[href="/admin"]')).toContainText("Admin");
  });

  test("admin user can access all protected routes", async ({ page }) => {
    await loginWithRoles(page, ["admin"]);

    // Test dashboard access
    await page.goto("/dashboard");
    await expect(page.locator('[data-testid="dashboard-page"]')).toBeVisible();

    // Test appointments access
    await page.goto("/appointments");
    await expect(page.locator('[data-testid="appointments-page"]')).toBeVisible();

    // Test billing access
    await page.goto("/billing");
    await expect(page.locator('[data-testid="billing-page"]')).toBeVisible();

    // Test admin access
    await page.goto("/admin");
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible();
  });

  test("non-admin user cannot access admin page", async ({ page }) => {
    await loginWithRoles(page, ["clinician"]);

    // Try to navigate to admin page
    await page.goto("/admin");

    // Should be redirected to unauthorized page
    await expect(page.locator('[data-testid="unauthorized-page"]')).toBeVisible();
    await expect(page.locator("h1")).toContainText("Unauthorized");
  });

  test("non-admin user cannot see admin navigation item", async ({ page }) => {
    await loginWithRoles(page, ["clinician"]);

    await page.goto("/dashboard");

    // Should not see admin link in navigation
    await expect(page.locator('nav a[href="/admin"]')).not.toBeVisible();
  });

  test("clinician user can access appointments but not admin", async ({ page }) => {
    await loginWithRoles(page, ["clinician"]);

    // Can access appointments
    await page.goto("/appointments");
    await expect(page.locator('[data-testid="appointments-page"]')).toBeVisible();

    // Cannot access admin
    await page.goto("/admin");
    await expect(page.locator('[data-testid="unauthorized-page"]')).toBeVisible();
  });

  test("front_desk user can access appointments but not admin or billing", async ({ page }) => {
    await loginWithRoles(page, ["front_desk"]);

    // Can access appointments
    await page.goto("/appointments");
    await expect(page.locator('[data-testid="appointments-page"]')).toBeVisible();

    // Cannot access billing
    await page.goto("/billing");
    await expect(page.locator('[data-testid="unauthorized-page"]')).toBeVisible();

    // Cannot access admin
    await page.goto("/admin");
    await expect(page.locator('[data-testid="unauthorized-page"]')).toBeVisible();
  });

  test("biller user can access billing but not admin", async ({ page }) => {
    await loginWithRoles(page, ["biller"]);

    // Can access billing
    await page.goto("/billing");
    await expect(page.locator('[data-testid="billing-page"]')).toBeVisible();

    // Cannot access admin
    await page.goto("/admin");
    await expect(page.locator('[data-testid="unauthorized-page"]')).toBeVisible();
  });

  test("dashboard quick actions are role-appropriate", async ({ page }) => {
    // Test admin user sees all actions
    await loginWithRoles(page, ["admin"]);
    await page.goto("/dashboard");

    await expect(page.locator('[data-testid="quick-action-appointments"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-action-billing"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-action-admin"]')).toBeVisible();

    // Test clinician user sees limited actions
    await loginWithRoles(page, ["clinician"]);
    await page.goto("/dashboard");

    await expect(page.locator('[data-testid="quick-action-appointments"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-action-billing"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="quick-action-admin"]')).not.toBeVisible();

    // Test front_desk user sees appropriate actions
    await loginWithRoles(page, ["front_desk"]);
    await page.goto("/dashboard");

    await expect(page.locator('[data-testid="quick-action-appointments"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-action-billing"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="quick-action-admin"]')).not.toBeVisible();

    // Test biller user sees appropriate actions
    await loginWithRoles(page, ["biller"]);
    await page.goto("/dashboard");

    await expect(page.locator('[data-testid="quick-action-appointments"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="quick-action-billing"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-action-admin"]')).not.toBeVisible();
  });

  test("unauthenticated user is redirected to login", async ({ page }) => {
    // Clear any existing auth state
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.clear();
    });

    // Try to access protected routes
    await page.goto("/admin");
    await expect(page.url()).toContain("/login");

    await page.goto("/dashboard");
    await expect(page.url()).toContain("/login");

    await page.goto("/appointments");
    await expect(page.url()).toContain("/login");

    await page.goto("/billing");
    await expect(page.url()).toContain("/login");
  });

  test("user with multiple roles has access to all their role-based routes", async ({ page }) => {
    await loginWithRoles(page, ["clinician", "biller"]);

    // Can access appointments (clinician role)
    await page.goto("/appointments");
    await expect(page.locator('[data-testid="appointments-page"]')).toBeVisible();

    // Can access billing (biller role)
    await page.goto("/billing");
    await expect(page.locator('[data-testid="billing-page"]')).toBeVisible();

    // Cannot access admin (no admin role)
    await page.goto("/admin");
    await expect(page.locator('[data-testid="unauthorized-page"]')).toBeVisible();
  });

  test("navigation guards work correctly on direct URL access", async ({ page }) => {
    await loginWithRoles(page, ["clinician"]);

    // Directly navigate to admin URL
    await page.goto("/admin");

    // Should be on unauthorized page
    await expect(page.url()).toContain("/unauthorized");
    await expect(page.locator('[data-testid="unauthorized-page"]')).toBeVisible();
  });

  test("role changes are reflected immediately", async ({ page }) => {
    // Start as clinician
    await loginWithRoles(page, ["clinician"]);

    await page.goto("/dashboard");
    await expect(page.locator('[data-testid="quick-action-admin"]')).not.toBeVisible();

    // Simulate role upgrade to admin
    const mockAdminUser = {
      id: "test-user-admin",
      email: "test@example.com",
      name: "Test User",
      roles: ["admin", "clinician"],
      provider: "auth0",
    };

    await page.evaluate((userData) => {
      localStorage.setItem("pms_user_data", JSON.stringify(userData));
    }, mockAdminUser);

    // Update API mock to return admin user
    await page.route("**/api/auth/user", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockAdminUser),
      });
    });

    // Refresh page to trigger re-authentication check
    await page.reload();

    // Should now see admin actions
    await expect(page.locator('[data-testid="quick-action-admin"]')).toBeVisible();

    // Should be able to access admin page
    await page.goto("/admin");
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible();
  });
});
