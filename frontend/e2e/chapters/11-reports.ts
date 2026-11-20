import { expect } from "@playwright/test";
import { DemoGuide } from "../support/DemoGuide";

/** Opens a report from the report list by its title. */
async function openReport(guide: DemoGuide, title: string): Promise<void> {
  await guide.nav(null, "Reports");
  await guide.typeInto(guide.page.getByPlaceholder("Find a report by name"), title);
  await guide.page.locator("main").getByRole("link", { name: new RegExp("^" + title.replace(/[/()]/g, "\\$&")) }).first().click();
  await guide.page.waitForURL(/\/reports\/[a-z0-9_-]+/);
  await guide.settle();
}

/** The report library: options, comparisons, exports, custom reports and scheduled emails. */
export async function reports(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Reports", "Profit and loss, balance sheet and 35 more reports");

  await guide.nav(null, "Reports");
  await guide.say("Reports are grouped by topic: business overview, who owes you, what you owe, sales, expenses, payroll, taxes and accounting.");
  await guide.scrollPage(700);
  await guide.scrollPage(-700);

  // ----- profit and loss with options -----
  await openReport(guide, "Profit and Loss");
  await expect(main.getByText(/Net income/i).first()).toBeVisible();
  await guide.say("Profit and Loss: income minus expenses for the period you choose.");
  await guide.choose("Show columns", "Months");
  await guide.settle();
  await guide.say("Split it into columns - by month, quarter, customer, class or location.");
  await guide.choose("Compare with", "Previous year");
  await guide.settle();
  await guide.choose("Accounting method", "Cash");
  await guide.settle();
  await guide.say("Switch between accrual and cash basis, and compare with an earlier period.");
  await guide.choose("Accounting method", "Accrual");
  await guide.choose("Compare with", "Nothing");
  await guide.settle();

  // ----- export -----
  await guide.say("Export any report to PDF, Excel or CSV, or print it.");
  const download = page.waitForEvent("download");
  await guide.click("Excel");
  expect((await download).suggestedFilename()).toMatch(/\.xlsx$/);

  // ----- save as custom -----
  await guide.click("Save as custom");
  const dialog = guide.dialog("Save as custom report");
  await guide.type("Name", "Monthly profit and loss", dialog);
  await guide.click("Save", dialog);
  await guide.settle();

  // ----- a tour of the main reports -----
  for (const [title, caption] of [
    ["Balance Sheet", "Balance Sheet: what the business owns, what it owes, and the owner's equity."],
    ["A/R Aging Summary", "A/R Aging: who owes you money and how overdue it is."],
    ["Sales by Customer Summary", "Sales by customer - and the same by product or service."],
    ["Project Profitability", "Project profitability, from the project we set up."],
    ["1099 Contractor Summary", "The 1099 summary lists contractors paid over the limit for the year."],
    ["General Ledger", "The general ledger: every transaction, account by account. Click a line to open the transaction."],
  ] as const) {
    await openReport(guide, title);
    await guide.say(caption);
  }

  // ----- schedule the custom report -----
  await guide.nav(null, "Reports");
  await guide.say("Custom reports are saved at the top. Any of them can be emailed on a schedule.");
  await main.getByRole("button", { name: "Email on a schedule" }).first().click();
  const schedule = guide.dialog();
  await guide.type("To (email addresses, separated by commas)", "owner@greenleaf.example.com", schedule);
  await guide.click("Save", schedule);
  await guide.settle();
}
