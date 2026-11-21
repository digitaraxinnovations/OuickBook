import crypto from "node:crypto";
import { expect } from "@playwright/test";
import { demoConfig } from "../demo.config";
import { DemoGuide } from "../support/DemoGuide";
import { appConfig } from "../../src/config/app.config";

/** Sign up, look around the screen, and fill in the company profile. */
export async function gettingStarted(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const company = demoConfig.company;

  await guide.open("/signup");
  await guide.chapter("Getting started", "Create your account and set up your company");
  await guide.say(`Welcome to ${appConfig.appName} - accounting for small businesses. Let's start by creating an account.`);

  const email = "demo+" + Date.now() + "@" + company.emailDomain;
  await guide.type("Your name", company.owner);
  await guide.type("Business name", company.name);
  await guide.type("Email", email);
  await guide.type("Password (at least 8 characters)", crypto.randomBytes(12).toString("base64url"));
  await guide.say(`${appConfig.appName} creates the company with a ready-made chart of accounts.`);
  await guide.click("Create account");
  // Creating the company and its chart of accounts can take a while on a busy machine.
  await page.waitForURL("**/dashboard", { timeout: demoConfig.expectTimeoutMs * 8 });
  await guide.settle();

  await guide.say("This is the dashboard: profit and loss, money owed to you, bills to pay and bank balances at a glance.");
  await guide.say("The sidebar on the left opens every part of the app. Click a group to open or close it.");
  await page.locator("aside").getByRole("button", { name: "Sales", exact: true }).click();
  await guide.pause(800);
  await page.locator("aside").getByRole("button", { name: "Sales", exact: true }).click();

  await page.locator("aside").getByRole("button", { name: "New", exact: true }).click();
  await guide.say("The + New button creates anything: invoices, payments, expenses, bills, deposits, journal entries and more.");
  await page.mouse.click(1300, 820);

  await page.getByPlaceholder("Search customers, vendors, invoices, amounts...").hover();
  await guide.say("Along the top: search everything, see notifications and recent transactions, and switch between companies.");

  // ----- company profile -----
  await guide.nav(null, "Settings");
  await guide.say("First, the company profile. These details are printed on invoices and other forms.");
  await guide.type("Email", "hello@" + company.website.replace("https://", ""));
  await guide.type("Phone", company.phone);
  await guide.type("Website", company.website);
  await guide.type("Address", company.address);
  await guide.click("Save");
  await expect(guide.field("Phone")).toHaveValue(company.phone);

  // ----- sales form style, late fees and reminders -----
  await guide.clickLink("Sales");
  await guide.say("On the Sales tab you choose the invoice template, colour and footer, and turn on late fees and reminders.");
  await guide.type("Footer message (printed on every invoice)", "Thank you for your business!");
  await page.getByText(/late fee/i).first().scrollIntoViewIfNeeded();
  await guide.say("Late fees and overdue reminders are added automatically by the daily job.");
  await guide.click("Save");

  // ----- payment terms -----
  await guide.clickLink("Payment terms");
  await guide.say("Payment terms set when invoices and bills are due. Let's add Net 45.");
  await guide.click("New terms");
  const dialog = guide.dialog();
  await guide.type("Name", "Net 45", dialog);
  await guide.type("Due in days", "45", dialog);
  await guide.click("Save", dialog);
  await guide.expectText("Net 45");

  await guide.clickLink("Expenses & advanced");
  await guide.say("Advanced settings: fiscal year, cash or accrual reports, bill terms, closing date and multi-currency. We'll come back here later.");
}
