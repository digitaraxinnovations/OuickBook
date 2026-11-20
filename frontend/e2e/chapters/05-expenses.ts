import path from "node:path";
import { expect, Locator } from "@playwright/test";
import { customers, products, vendors } from "../demo-data";
import { DemoGuide } from "../support/DemoGuide";

/** The category drop-down in a purchase line (its first option says "Choose a category"). */
function categorySelect(guide: DemoGuide, row: Locator): Locator {
  return row.locator("select", { has: guide.page.locator("option", { hasText: "Choose a category" }) }).first();
}

/** Vendors, expenses, checks, bills, paying bills, purchase orders, vendor credits, receipts and mileage. */
export async function expenses(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Expenses and bills", "Everything you buy, and paying the people you buy from");

  // ----- vendors -----
  await guide.nav("Expenses", "Vendors");
  await guide.say("Vendors are the businesses and people you buy from.");
  await guide.click("New vendor");
  const form = guide.dialog("New vendor");
  await guide.type("Display name", vendors.main.display_name, form);
  await guide.type("Company name", vendors.main.company_name, form);
  await guide.type("Email", vendors.main.email, form);
  await guide.type("Phone", vendors.main.phone, form);
  await guide.click("Save", form);
  await guide.expectText(vendors.main.display_name);

  for (const vendor of vendors.others) {
    await guide.api("POST", "/vendors", vendor);
  }
  const contractors = await guide.api<{ id: number; display_name: string }[]>("GET", "/vendors");
  const contractor = contractors.find((v) => v.display_name === vendors.others[2].display_name)!;
  await guide.api("PUT", "/vendors/" + contractor.id, { ...vendors.others[2], track_1099: true, tax_id: "12-3456789" });
  await page.reload();
  await guide.settle();
  await guide.say("We added a few more. The contractor is marked 'Track payments for 1099', so they appear on the 1099 report.");

  // ----- expense -----
  await guide.newMenu("Expense");
  await guide.say("An expense is money spent right away - from the bank account or a credit card.");
  await guide.choose("Payee", vendors.others[0].display_name);
  await guide.choose("Payment account", /Checking/);
  let row = guide.lineRow(0);
  await guide.chooseIn(categorySelect(guide, row), /Utilities/);
  await guide.typeInto(row.locator("input:not([type])").first(), "Electricity - October");
  await guide.typeInto(row.locator('input[type="number"]').last(), "145.20");
  await guide.say("Each line goes to a category - an expense account - so your reports show where the money went.");
  await guide.click("Save expense");
  await page.waitForURL(/\/expenses\/\d+$/);
  await guide.settle();

  // ----- billable expense -----
  await guide.newMenu("Expense");
  await guide.say("Expenses can be billable: tick a customer and the cost is offered on their next invoice.");
  await guide.choose("Payee", vendors.main.display_name);
  await guide.choose("Payment account", /Credit Card/);
  row = guide.lineRow(0);
  await guide.chooseIn(categorySelect(guide, row), /Repairs/);
  await guide.typeInto(row.locator("input:not([type])").first(), "Bird bath for the sanctuary garden");
  await guide.typeInto(row.locator('input[type="number"]').last(), "89.00");
  await guide.chooseIn(row.locator("select").last(), customers.main.display_name);
  await guide.click("Save expense");
  await page.waitForURL(/\/expenses\/\d+$/);
  await guide.settle();

  // ----- check -----
  await guide.newMenu("Check");
  await guide.say("Writing a check works the same way. Tick Print later to print a batch of checks at once.");
  await guide.choose("Payee", vendors.others[2].display_name);
  await guide.choose("Bank account", /Checking/);
  await guide.checkbox("Print later").check();
  row = guide.lineRow(0);
  await guide.chooseIn(categorySelect(guide, row), /Contractors/);
  await guide.typeInto(row.locator("input:not([type])").first(), "Tree removal - subcontract");
  await guide.typeInto(row.locator('input[type="number"]').last(), "650.00");
  await guide.click("Save check");
  await page.waitForURL(/\/expenses\/\d+$/);
  await guide.settle();

  // ----- purchase order -> bill -----
  await guide.newMenu("Purchase order");
  await guide.say("Ordering stock? A purchase order tells the vendor what you want. It doesn't affect your books until the bill arrives.");
  await guide.choose("Vendor", vendors.main.display_name);
  row = guide.lineRow(0);
  await guide.chooseIn(row.locator("select").first(), products.inventory.name);
  await guide.typeInto(row.locator('input[type="number"]').first(), "20");
  await guide.click("Save purchase order");
  await page.waitForURL(/\/expenses\/forms\/purchase-orders\/\d+$/);
  await guide.settle();

  await guide.say("When the goods and the bill arrive, turn the purchase order into a bill.");
  await guide.click("Create bill");
  const convert = guide.dialog();
  await guide.type("Vendor's bill no.", "GS-5521", convert);
  await guide.click("Create bill", convert);
  await page.waitForURL(/\/expenses\/forms\/bills\/\d+$/);
  await guide.settle();
  await guide.say("The bill adds the 20 bags to inventory and records what you owe Green Supply Co.");

  // ----- bill entered directly -----
  await guide.newMenu("Bill");
  await guide.say("Bills can also be entered directly - for example the monthly power bill, due in 30 days.");
  await guide.choose("Vendor", vendors.others[0].display_name);
  row = guide.lineRow(0);
  await guide.chooseIn(categorySelect(guide, row), /Utilities/);
  await guide.typeInto(row.locator('input[type="number"]').last(), "212.40");
  await guide.click("Save bill");
  await page.waitForURL(/\/expenses\/forms\/bills\/\d+$/);
  await guide.settle();

  // ----- vendor credit -----
  await guide.newMenu("Vendor credit");
  await guide.say("A vendor credit records a refund or credit from a vendor - here, two damaged bags sent back.");
  await guide.choose("Vendor", vendors.main.display_name);
  row = guide.lineRow(0);
  await guide.chooseIn(row.locator("select").first(), products.inventory.name);
  await guide.typeInto(row.locator('input[type="number"]').first(), "2");
  await guide.click("Save vendor credit");
  await page.waitForURL(/\/expenses\/forms\/vendor-credits\/\d+$/);
  await guide.settle();

  // ----- pay bills -----
  await guide.nav("Expenses", "Pay bills");
  await guide.say("Pay bills lists everything you owe. Tick the bills to pay; vendor credits are used up automatically.");
  await guide.choose("Pay from", /Checking/);
  const billBoxes = main.locator('tbody input[type="checkbox"]');
  await expect(billBoxes.first()).toBeVisible();
  const count = await billBoxes.count();
  for (let i = 0; i < count; i++) {
    await billBoxes.nth(i).check();
  }
  await guide.click("Save payments");
  await guide.settle();
  await guide.nav("Expenses", "Bill payments");
  await guide.say("One payment is made per vendor. The bills are now paid.");

  // ----- receipts -----
  await guide.nav("Expenses", "Receipts");
  await guide.say("Snap a photo of a receipt and upload it. Then turn it into an expense with the image attached.");
  await main.locator('input[type="file"]').setInputFiles(path.join(__dirname, "..", "fixtures", "receipt.png"));
  await guide.expectText("receipt.png");
  await guide.clickLink("Create expense");
  await guide.choose("Payee", vendors.others[1].display_name);
  await guide.choose("Payment account", /Credit Card/);
  row = guide.lineRow(0);
  await guide.chooseIn(categorySelect(guide, row), /Travel/);
  await guide.typeInto(row.locator('input[type="number"]').last(), "62.75");
  await guide.click("Save expense");
  await page.waitForURL(/\/expenses\/\d+$/);
  await guide.settle();
  await guide.say("The receipt image is attached to the expense.");

  // ----- mileage -----
  await guide.nav("Expenses", "Mileage");
  await guide.say("Log business trips for your mileage deduction.");
  await guide.click("Add trip");
  const trip = guide.dialog();
  await guide.type("Miles", "34", trip);
  await guide.type("From", "Office", trip);
  await guide.type("To", "Amy's Bird Sanctuary", trip);
  await guide.click("Save trip", trip);
  await guide.expectText(/34/);

  // ----- print checks -----
  await guide.nav("Expenses", "Print checks");
  await guide.say("Checks saved with Print later wait here. Pick the bank account and starting number, then print them on check paper.");
  await guide.nav("Expenses", "Expenses & checks");
  await guide.say("All expenses and checks in one list.");
}
