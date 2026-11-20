import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect } from "@playwright/test";
import { customers, teammate } from "../demo-data";
import { isoDate } from "../support/dates";
import { DemoGuide } from "../support/DemoGuide";

/** Users and roles, closing the books, the audit log, import/export, API and webhooks, and everyday tools. */
export async function companyAdmin(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");
  const topBar = page.locator("header, [role=banner]").first();

  await guide.chapter("Running the company", "Users, closing the books, audit log, import and export, and integrations");

  // ----- users -----
  await guide.nav(null, "Settings");
  await guide.clickLink("Users");
  await guide.say("Invite your team or your accountant. Each person gets a role that decides what they can see and change.");
  await guide.click("Invite a user");
  let dialog = guide.dialog();
  await guide.type("Email", teammate.email, dialog);
  await guide.choose("Role", new RegExp("^" + teammate.role), dialog);
  await guide.click("Send invitation", dialog);
  await guide.expectText(teammate.email);
  await guide.say("Roles go from full admin to sales-only, purchases-only, reports-only and time-only. The invitation link arrives by email.");

  // ----- closing date -----
  await guide.clickLink("Expenses & advanced");
  await guide.say("After filing taxes, close the books: nothing dated on or before the closing date can change without the closing password.");
  const password = "close-" + Date.now();
  await guide.setDate("Closing date", isoDate(-1));
  await guide.type("Closing password", password);
  await guide.click("Save");
  await guide.settle();

  await guide.newMenu("Journal entry");
  await guide.say("Let's try to post something into the closed period...");
  await guide.setDate("Date", isoDate(-2));
  const first = guide.lineRow(0);
  await guide.chooseIn(first.locator("select").first(), /Office Supplies/);
  await guide.typeInto(first.locator('input[type="number"]').nth(0), "40");
  const second = guide.lineRow(1);
  await guide.chooseIn(second.locator("select").first(), /Checking/);
  await guide.typeInto(second.locator('input[type="number"]').nth(1), "40");
  await guide.type("Memo", "Late adjustment");
  guide.promptAnswer = password;
  await guide.say("Ledgerly asks for the closing password. Without it, the change is refused.");
  await guide.click("Save journal entry");
  await page.waitForURL(/\/accounting\/journal-entries$/);
  await guide.settle();

  // ----- audit log -----
  await guide.nav(null, "Settings");
  await guide.clickLink("Audit log");
  await guide.say("The audit log records every change: who made it, when, and the old and new values.");
  await expect(main.getByText(/Sam Rivera/).first()).toBeVisible();
  await guide.scrollPage(500);
  await guide.scrollPage(-500);

  // ----- import / export -----
  await guide.clickLink("Import & export");
  await guide.say("Move customers, vendors, accounts and transactions in and out as CSV files - Excel opens and saves them.");
  const csv = path.join(os.tmpdir(), "ledgerly-demo-vendors-" + Date.now() + ".csv");
  fs.writeFileSync(csv, "Name,Company,Email,Phone\nPrairie Seed Co,Prairie Seed Co,sales@prairieseed.example.com,(555) 700-1100\nAce Tool Rental,Ace Tool Rental,,(555) 700-2200\n");
  await main.locator('input[type="file"]').nth(1).setInputFiles(csv);
  await guide.expectText(/2/);
  await guide.say("Two vendors imported. Imports are all or nothing - one bad row and nothing is changed.");
  const download = page.waitForEvent("download");
  await main.getByRole("button", { name: "Export CSV" }).first().click();
  expect((await download).suggestedFilename()).toMatch(/\.csv$/);

  // ----- API and webhooks -----
  await guide.clickLink("API & webhooks");
  await guide.say("Connect other programs through the REST API. Create an API key for each program.");
  await guide.type("Key name", "Online store");
  await guide.click("Create key");
  await guide.expectText(/Copy this key now/);
  await guide.say("Webhooks tell other programs the moment something changes - a new invoice, a payment, a new customer.");
  await guide.type("URL", "https://hooks.example.com/ledgerly");
  await guide.click("Add webhook");
  await guide.expectText("https://hooks.example.com/ledgerly");

  await guide.clickLink("Email log");
  await guide.say("The email log keeps every email Ledgerly sent: invoices, reminders, invitations and scheduled reports.");

  // ----- everyday tools: search, recent, notifications -----
  await guide.nav(null, "Dashboard");
  await guide.say("A few everyday tools in the top bar.");
  const search = page.getByPlaceholder("Search customers, vendors, invoices, amounts...");
  await guide.typeInto(search, "Amy");
  await guide.say("Search finds customers, vendors, transactions, products and accounts - even amounts.");
  await page.getByRole("button", { name: new RegExp(customers.main.display_name) }).first().click();
  await guide.settle();

  await page.getByRole("button", { name: "Recent transactions" }).click();
  await guide.say("Recent transactions takes you back to what you were working on.");
  await page.keyboard.press("Escape");
  await page.mouse.click(900, 500);

  await page.getByRole("button", { name: "Notifications" }).click();
  await guide.say("Notifications point out what needs attention: overdue invoices, bills due, low stock, bank lines to review.");
  await page.mouse.click(900, 500);

  // ----- several companies -----
  await page.getByRole("button", { name: "Greenleaf Landscaping" }).first().click();
  await guide.say("One login can run several companies. Switch between them here, or add a new one.");
  await page.mouse.click(900, 500);
  await guide.nav(null, "Dashboard");
  await guide.say("Back on the dashboard, every number now reflects the work we just did.");
  await topBar.isVisible();
}
