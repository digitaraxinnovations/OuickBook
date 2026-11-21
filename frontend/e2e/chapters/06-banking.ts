import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, Locator } from "@playwright/test";
import { vendors } from "../demo-data";
import { DemoGuide } from "../support/DemoGuide";
import { appConfig } from "../../src/config/app.config";

interface AccountRow {
  id: number;
  name: string;
  balance: string;
}

/** Today's local date as YYYY-MM-DD (the same day the app uses). */
function today(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
}

/** A bank statement (CSV) whose lines match what was recorded earlier, plus a few new ones. */
function writeStatement(depositTotal: string): string {
  const rows = [
    ["Date", "Description", "Amount"],
    [today(), "MOBILE DEPOSIT", depositTotal],
    [today(), "CITY POWER & LIGHT AUTOPAY", "-145.20"],
    [today(), "SHELL OIL 4421 SPRINGFIELD", "-48.30"],
    [today(), "MONTHLY SERVICE FEE", "-12.00"],
    [today(), "PERSONAL - CORNER COFFEE", "-6.50"],
  ];
  const file = path.join(os.tmpdir(), "demo-statement-" + Date.now() + ".csv");
  fs.writeFileSync(file, rows.map((row) => row.join(",")).join("\n"));
  return file;
}

/** The row of the review table whose text contains this description. */
function bankRow(main: Locator, description: string): Locator {
  return main.locator("tbody tr", { hasText: description }).first();
}

/** Deposits, statement upload, matching and categorizing, rules, transfers and reconciling. */
export async function banking(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Banking", "Deposits, bank statements, rules, transfers and reconciling");

  // ----- bank deposit -----
  await guide.newMenu("Bank deposit");
  await guide.say("Customer payments wait in Undeposited Funds. A bank deposit moves them into the bank - one deposit, like the slip you take to the bank.");
  await guide.choose("Deposit to", /Checking/);
  const selectAll = main.locator('thead input[type="checkbox"]').first();
  await expect(main.locator('tbody input[type="checkbox"]').first()).toBeVisible();
  await selectAll.check();
  const totalText = await main.getByText(/Deposit total/i).first().locator("..").innerText().catch(() => "");
  await guide.click("Save deposit");
  await page.waitForURL(/\/banking\/deposits$/);
  await guide.settle();

  const deposits = await guide.api<{ total: string }[]>("GET", "/deposits");
  const depositTotal = deposits[0]?.total ?? totalText.replace(/[^0-9.]/g, "");

  // ----- upload a statement -----
  await guide.nav("Banking", "Bank transactions");
  await guide.say("Bank transactions is where your bank's activity comes in. Without a live bank feed, upload the statement file from your bank.");
  await main.getByRole("button", { name: /Checking/ }).first().click();
  await guide.settle();
  await guide.click("Upload statement");
  const upload = guide.dialog();
  await upload.locator('input[type="file"]').setInputFiles(writeStatement(String(depositTotal)));
  await guide.say(`CSV, OFX and QFX files work. ${appConfig.appName} finds the date, description and amount columns itself.`);
  await guide.click("Import", upload);
  await expect(bankRow(main, "MOBILE DEPOSIT")).toBeVisible();
  await guide.say(`Each statement line now waits For review. ${appConfig.appName} suggests a match when it finds the same amount in your books.`);

  // ----- match -----
  await bankRow(main, "MOBILE DEPOSIT").getByRole("button", { name: "Match" }).click();
  let dialog = guide.dialog();
  await guide.say("This deposit is the one we just recorded - match it, so it isn't counted twice.");
  await dialog.getByRole("button", { name: "Match" }).first().click();
  await guide.settle();

  await bankRow(main, "CITY POWER").getByRole("button", { name: "Match" }).click();
  dialog = guide.dialog();
  await dialog.getByRole("button", { name: "Match" }).first().click();
  await guide.settle();

  // ----- add -----
  await guide.say("Lines that aren't in your books yet are added: pick the payee and category.");
  await bankRow(main, "SHELL OIL").getByRole("button", { name: "Add" }).click();
  dialog = guide.dialog();
  await guide.choose("Payee", vendors.others[1].display_name, dialog);
  await guide.chooseIn(dialog.locator("select", { has: page.locator("option", { hasText: "Choose" }) }).last(), /Travel/);
  await guide.click("Add", dialog);

  await bankRow(main, "MONTHLY SERVICE FEE").getByRole("button", { name: "Add" }).click();
  dialog = guide.dialog();
  await guide.chooseIn(dialog.locator("select", { has: page.locator("option", { hasText: "Choose" }) }).last(), /Bank Charges/);
  await guide.click("Add", dialog);

  // ----- exclude -----
  await guide.say("Exclude lines that don't belong in the business books, like a personal purchase.");
  await bankRow(main, "PERSONAL").getByRole("button", { name: "Exclude" }).click();
  await guide.settle();
  await guide.say("The review list is empty. The Added, Matched and Excluded tabs show what happened to each line, with Undo.");

  // ----- rules -----
  await guide.nav("Banking", "Bank rules");
  await guide.say("Bank rules do the categorizing for you. From now on, every SHELL purchase goes to Travel automatically.");
  await guide.click("New rule");
  dialog = guide.dialog("New rule");
  await guide.type("Rule name", "Fuel purchases", dialog);
  await guide.choose("Apply to", "Money out", dialog);
  await guide.typeInto(dialog.locator('input:not([type="number"]):not([type="checkbox"])').nth(1), "SHELL");
  await guide.choose("Then categorize as", /Travel/, dialog);
  await guide.choose("Payee", vendors.others[1].display_name, dialog);
  await guide.click("Save rule", dialog);
  await guide.expectText("Fuel purchases");

  // ----- transfer -----
  await guide.nav("Banking", "Transfers");
  await guide.say("Transfers move money between your own accounts - for example into savings, or paying off the credit card.");
  await guide.click("New transfer");
  dialog = guide.dialog("New transfer");
  await guide.choose("Transfer from", /Checking/, dialog);
  await guide.choose("Transfer to", /Savings/, dialog);
  await guide.type("Amount", "500", dialog);
  await guide.type("Memo", "Move to savings", dialog);
  await guide.click("Save", dialog);
  await guide.expectText("Move to savings");

  // ----- reconcile -----
  const accounts = await guide.api<AccountRow[]>("GET", "/accounts");
  const checking = accounts.find((account) => account.name === "Checking")!;

  await guide.nav("Banking", "Reconcile");
  await guide.say("Once a month, reconcile: check your books against the bank statement so you know every transaction is right.");
  await guide.choose("Account", /Checking/);
  await guide.type("Statement ending balance", String(checking.balance));
  await guide.click("Start reconciling");
  await page.waitForURL(/\/banking\/reconcile\/\d+$/);
  await guide.settle();
  await guide.say("Tick each transaction that appears on the statement. When the difference is zero, you're done.");
  const rows = main.locator("tbody tr.cursor-pointer");
  const count = await rows.count();
  // Lines matched from the bank statement are already ticked.
  for (let i = 0; i < count; i++) {
    if (!(await rows.nth(i).locator('input[type="checkbox"]').isChecked())) {
      await rows.nth(i).click();
    }
  }
  await guide.click("Finish now");
  await guide.settle();
  await guide.say("Reconciled. A reconciliation report is saved for each statement.");
}
