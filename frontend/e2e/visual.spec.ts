import { expect, test } from "@playwright/test";

test("workspace visual baseline is styled, not raw HTML", async ({ page }) => {
  await page.goto("/");
  const app = page.locator("main");
  await expect(app).toBeVisible();
  const background = await app.evaluate((node) => getComputedStyle(node).backgroundColor);
  expect(background).not.toBe("rgba(0, 0, 0, 0)");
  await page.screenshot({ fullPage: true });
});
