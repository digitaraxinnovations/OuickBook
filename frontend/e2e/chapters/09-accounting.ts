import { customers, products } from "../demo-data";
import { isoDate } from "../support/dates";
import { DemoGuide } from "../support/DemoGuide";
import { appConfig } from "../../src/config/app.config";

/** Chart of accounts, journal entries and recurring transactions. */
export async function accounting(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Accounting", "Chart of accounts, journal entries and recurring transactions");

  // ----- chart of accounts -----
  await guide.nav("Accounting", "Chart of accounts");
  await guide.say(`The chart of accounts lists every account in your books, with its balance. ${appConfig.appName} set up a standard one for you.`);
  await guide.scrollPage(600);
  await guide.scrollPage(-600);
  await guide.click("New account");
  const dialog = guide.dialog("New account");
  await guide.choose("Account type", "Expense", dialog);
  await guide.type("Detail type", "Auto expenses", dialog);
  await guide.type("Number", "6150", dialog);
  await guide.type("Name", "Vehicle fuel", dialog);
  await guide.type("Description", "Fuel for the work trucks", dialog);
  await guide.say("Accounts can have numbers, sub-accounts, and a tax category or 1099 box.");
  await guide.click("Save", dialog);
  await guide.expectText("Vehicle fuel");

  // ----- journal entry -----
  await guide.newMenu("Journal entry");
  await guide.say("Journal entries are for anything that isn't a normal form - here, the owner puts more money into the business.");
  const first = guide.lineRow(0);
  await guide.chooseIn(first.locator("select").first(), /Checking/);
  await guide.typeInto(first.locator('input[type="number"]').nth(0), "5000");
  const second = guide.lineRow(1);
  await guide.chooseIn(second.locator("select").first(), /Owner's Investment/);
  await guide.typeInto(second.locator('input[type="number"]').nth(1), "5000");
  await guide.type("Memo", "Owner investment");
  await guide.say("Debits must equal credits before it can be saved.");
  await guide.click("Save journal entry");
  await page.waitForURL(/\/accounting\/journal-entries$/);
  await guide.settle();
  await guide.say("The journal shows every entry - including the ones invoices, bills and payroll made automatically.");

  // ----- recurring -----
  await guide.nav("Accounting", "Recurring transactions");
  await guide.say("Recurring templates create invoices, bills, expenses or journal entries on a schedule - perfect for monthly contracts.");
  await guide.click("New template");
  const template = guide.dialog();
  await guide.choose("Transaction type", "Invoice", template);
  await guide.type("Template name", "Monthly lawn care - " + customers.main.display_name, template);
  await guide.type("Every", "1", template);
  await guide.choose("Period", "Month(s)", template);
  await guide.setDate("Start date", isoDate(), template);
  await guide.choose("Customer", customers.main.display_name, template);
  await guide.fillLine(0, products.service.name, "4", undefined, template);
  await guide.click("Save template", template);
  await guide.expectText(/Monthly lawn care/);

  await guide.say("The daily job runs due templates automatically. Run due does it right now.");
  await guide.click("Run due");
  await guide.settle();
  await main.getByText(/Monthly lawn care/).first().hover();
}
