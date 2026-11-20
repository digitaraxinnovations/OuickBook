import { expect } from "@playwright/test";
import { customers, products, project } from "../demo-data";
import { isoDate } from "../support/dates";
import { DemoGuide } from "../support/DemoGuide";

/** Projects, classes, locations, tags and budgets. */
export async function projectsAndTracking(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Projects, tracking and budgets", "See profit per job, slice your numbers, and plan ahead");

  // ----- classes, locations, tags -----
  await guide.nav("Accounting", "Classes, locations & tags");
  await guide.say("Classes, locations and tags are extra ways to slice income and expenses - for example by type of customer or by branch.");
  const addButtons = main.getByRole("button", { name: "Add", exact: true });

  for (const name of ["Residential", "Commercial"]) {
    await addButtons.nth(0).click();
    const dialog = guide.dialog("Class");
    await guide.type("Name", name, dialog);
    await guide.click("Save", dialog);
    await guide.expectText(name);
  }
  for (const name of ["North branch", "South branch"]) {
    await addButtons.nth(1).click();
    const dialog = guide.dialog("Location");
    await guide.type("Name", name, dialog);
    await guide.click("Save", dialog);
    await guide.expectText(name);
  }
  await addButtons.nth(2).click();
  let dialog = guide.dialog("Tag");
  await guide.type("Tag", "Spring promo", dialog);
  await guide.type("Group", "Campaigns", dialog);
  await guide.click("Save", dialog);
  await guide.expectText("Spring promo");
  await guide.say("Once added, Class, Location and Tags fields appear on invoices, expenses, bills and journal entries, and every report can be filtered by them.");

  // ----- project -----
  await guide.nav(null, "Projects");
  await guide.say("Projects track income, costs and profit for one job.");
  await guide.click("New project");
  dialog = guide.dialog("New project");
  await guide.type("Project name", project.name, dialog);
  await guide.choose("Customer", customers.main.display_name, dialog);
  await guide.setDate("Start date", isoDate(), dialog);
  await guide.click("Save", dialog);
  await guide.expectText(project.name);

  await main.getByText(project.name, { exact: true }).first().click();
  await page.waitForURL(/\/projects\/\d+$/);
  await guide.settle();
  await guide.say("Invoice the work, and pick the project on the invoice - along with a class and location.");
  await guide.clickLink("New invoice");
  await guide.choose("Customer", customers.main.display_name);
  await guide.choose("Project", project.name);
  await guide.fillLine(0, products.others[1].name, "3");
  await guide.choose("Class", "Residential");
  await guide.choose("Location", "North branch");
  await guide.click("Save invoice");
  await page.waitForURL(/\/sales\/invoices\/\d+$/);
  await guide.settle();

  await guide.nav(null, "Projects");
  await main.getByText(project.name, { exact: true }).first().click();
  await page.waitForURL(/\/projects\/\d+$/);
  await guide.settle();
  await expect(main.getByText(/Income/).first()).toBeVisible();
  await guide.say("The project page adds up its income, costs and labor, and shows the profit.");

  // ----- budget -----
  await guide.nav("Accounting", "Budgets");
  await guide.say("Budgets plan income and expenses month by month. Later you can compare them with what really happened.");
  await guide.click("New budget");
  dialog = guide.dialog("New budget");
  await guide.type("Name", "Plan " + new Date().getFullYear(), dialog);
  await guide.click("Create", dialog);
  await page.waitForURL(/\/accounting\/budgets\/\d+$/);
  await guide.settle();

  const salesRow = main.locator("tbody tr", { hasText: "Sales" }).first();
  await guide.typeInto(salesRow.locator('input[type="number"]').first(), "4000");
  await salesRow.getByRole("button", { name: "Copy Jan across" }).click();
  const utilitiesRow = main.locator("tbody tr", { hasText: "Utilities" }).first();
  await guide.scrollTo(utilitiesRow);
  await guide.typeInto(utilitiesRow.locator('input[type="number"]').first(), "350");
  await utilitiesRow.getByRole("button", { name: "Copy Jan across" }).click();
  await guide.say("Type January's amount and copy it across the year.");
  await guide.click("Save budget");
  await guide.click("Budget vs actual");
  await guide.say("Budget vs actual shows how you're doing against the plan.");
}
