import { expect, test } from "@playwright/test";

test("loads CTO intelligence workspace chrome", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Intelligence OS")).toBeVisible();
  const primaryNav = page.getByRole("navigation", { name: "Primary navigation" });
  const contextNav = page.getByRole("navigation", { name: "Context navigation" });

  await expect(primaryNav.getByRole("button", { name: /Executive/ })).toBeVisible();
  await expect(primaryNav.getByRole("button", { name: /Knowledge Graph/ })).toBeVisible();
  await expect(primaryNav.getByRole("button", { name: /Risk Center/ })).toBeVisible();

  await primaryNav.getByRole("button", { name: /Risk Center/ }).click();
  await expect(contextNav.getByRole("button", { name: /Security/ })).toBeVisible();
  await expect(contextNav.getByRole("button", { name: /PR Risk/ })).toBeVisible();
  await expect(contextNav.getByRole("button", { name: /Drift/ })).toBeVisible();
});
