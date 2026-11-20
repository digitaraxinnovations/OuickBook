import { expect } from "@playwright/test";
import { currency, customers, products } from "../demo-data";
import { isoDate } from "../support/dates";
import { DemoGuide } from "../support/DemoGuide";

/** Foreign customers: turn on multicurrency, add a currency and rate, invoice and get paid. */
export async function multicurrency(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Multicurrency", "Invoice customers in their own currency");

  await guide.nav(null, "Settings");
  await guide.clickLink("Expenses & advanced");
  await guide.say("Selling abroad? Turn on multicurrency in the advanced settings.");
  await guide.checkbox(/Multicurrency/).check();
  await guide.click("Save");

  await guide.clickLink("Currencies");
  await guide.say("Add the currencies you use and their exchange rates. A rates service can fill these in automatically when connected.");
  await guide.type("Code", currency.code);
  await guide.type("Name", "Euro");
  await guide.click("Add currency");
  await guide.choose("Currency", new RegExp(currency.code));
  await guide.setDate("Date", isoDate());
  await guide.type("1 unit = how many USD", currency.rate);
  await guide.click("Save rate");
  await guide.expectText(currency.rate);

  // ----- foreign customer -----
  await guide.nav("Sales", "Customers");
  await guide.click("New customer");
  const form = guide.dialog("New customer");
  await guide.type("Display name", customers.foreign.display_name, form);
  await guide.type("Email", customers.foreign.email, form);
  await guide.choose("Currency", new RegExp("^" + currency.code), form);
  await guide.say("This customer is invoiced in euros.");
  await guide.click("Save", form);
  await guide.expectText(customers.foreign.display_name);

  // ----- invoice in euros -----
  await guide.newMenu("Invoice");
  await guide.choose("Customer", customers.foreign.display_name);
  await guide.say("The invoice is in euros. Ledgerly uses the saved rate to record it in dollars in your books.");
  await guide.fillLine(0, products.others[1].name, "5");
  await guide.click("Save invoice");
  await page.waitForURL(/\/sales\/invoices\/\d+$/);
  await guide.settle();
  await expect(main.getByText(/€/).first()).toBeVisible();

  // ----- payment at a different rate -----
  await guide.clickLink("Receive payment");
  await expect(main.locator('tbody input[type="checkbox"]').first()).toBeChecked();
  await guide.type("Exchange rate (1 " + currency.code + " = ? USD)", currency.paymentRate);
  await guide.say("By the time they pay, the euro is worth more. The difference is booked as an exchange gain automatically.");
  await guide.click("Save payment");
  await page.waitForURL(/\/sales\/payments$/);
  await guide.settle();
}
