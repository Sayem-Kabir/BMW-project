import { test, expect } from "@playwright/test";

/**
 * Spec Phase 10A — register/login → role-scoped dashboard.
 * Requires frontend :3000 and API :8000 with seeded users.
 *
 *   cd apps/frontend && npx playwright install
 *   npx playwright test
 */

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000";

test.describe("role dashboards", () => {
  test("landing shows login only", async ({ page }) => {
    await page.goto(BASE + "/");
    await expect(page.getByRole("link", { name: "Login" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Demo Mode" })).toHaveCount(0);
  });

  test("fleet manager lands on fleet dashboard", async ({ page }) => {
    await page.goto(BASE + "/login");
    await page.fill('input[type="email"], input[name="email"]', "demo@bmwai.dev");
    await page.fill('input[type="password"], input[name="password"]', "demo1234");
    await page.getByRole("button", { name: /sign in|login/i }).click();
    await page.waitForURL(/\/fleet\/dashboard/, { timeout: 20000 });
    await expect(page).toHaveURL(/\/fleet\/dashboard/);
  });

  test("driver lands on driver dashboard", async ({ page }) => {
    await page.goto(BASE + "/login");
    await page.fill('input[type="email"], input[name="email"]', "driver@bmwai.dev");
    await page.fill('input[type="password"], input[name="password"]', "driver1234");
    await page.getByRole("button", { name: /sign in|login/i }).click();
    await page.waitForURL(/\/driver\/dashboard/, { timeout: 20000 });
    await expect(page).toHaveURL(/\/driver\/dashboard/);
  });

  test("admin lands on admin dashboard", async ({ page }) => {
    await page.goto(BASE + "/login");
    await page.fill('input[type="email"], input[name="email"]', "admin@bmwai.dev");
    await page.fill('input[type="password"], input[name="password"]', "admin1234");
    await page.getByRole("button", { name: /sign in|login/i }).click();
    await page.waitForURL(/\/admin\/dashboard/, { timeout: 20000 });
    await expect(page).toHaveURL(/\/admin\/dashboard/);
  });
});
