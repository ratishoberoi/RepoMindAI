import { expect, test } from "@playwright/test";

test("loads CTO intelligence workspace chrome", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Intelligence OS")).toBeVisible();
  await expect(page.getByRole("button", { name: /Executive/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Knowledge/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Security/ })).toBeVisible();
});
