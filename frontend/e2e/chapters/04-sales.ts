import { expect } from "@playwright/test";
import { customers, products, tax } from "../demo-data";
import { DemoGuide } from "../support/DemoGuide";

const taxPattern = new RegExp(tax.rateName);

/** Estimate to invoice, emailing, the customer portal, payments and the other sales forms. */
export async function sales(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Selling", "Estimates, invoices, payments and every other sales form");

  // ----- estimate -----
  await guide.newMenu("Estimate");
  await guide.say("Start with an estimate: a price quote the customer can accept before any work begins.");
  await guide.choose("Customer", customers.main.display_name);
  await guide.fillLine(0, products.others[1].name, "2");
  await guide.click("Add line");
  await guide.fillLine(1, products.inventory.name, "4");
  await guide.say("Picking a product fills in its description and price. The amounts and totals update as you type.");
  await guide.chooseIn(guide.selectWithOption("No sales tax"), taxPattern);
  await guide.say("Choose the sales tax rate at the bottom; Ledgerly adds the tax on taxable lines.");
  await guide.click("Save estimate");
  await page.waitForURL(/\/sales\/forms\/estimates\/\d+$/);
  await guide.settle();

  await guide.say("The customer said yes. Mark the estimate accepted, then turn it into an invoice with one click.");
  await guide.click("Mark accepted");
  await guide.click("Create invoice");
  const convert = guide.dialog("Create invoice from estimate");
  await guide.say("You can invoice the whole estimate or just part of it, for example a 50% deposit.");
  await guide.click("Create invoice", convert);
  await page.waitForURL(/\/sales\/invoices\/\d+$/);
  await guide.settle();
  await guide.say("Here is the invoice, linked back to its estimate.");

  // ----- invoice from scratch -----
  await guide.nav("Sales", "Invoices");
  await guide.say("Invoices can also be created from scratch.");
  await guide.clickLink("Create invoice");
  await guide.choose("Customer", customers.others[0].display_name);
  await guide.choose("Terms", "Net 30");
  await guide.fillLine(0, products.service.name, "4");
  await guide.say("Lawn mowing comes in 10% cheaper: the Spring sale price rule applied automatically.");
  await guide.click("Add line");
  await guide.fillLine(1, products.others[0].name, "3");
  await guide.chooseIn(guide.selectWithOption("No sales tax"), taxPattern);
  await guide.type("Message on invoice", "Thanks for choosing Greenleaf!");
  await guide.click("Save invoice");
  await page.waitForURL(/\/sales\/invoices\/\d+$/);
  await guide.settle();
  const invoiceId = guide.idFromUrl();
  await guide.expectText("Balance due");

  // ----- email -----
  await guide.say("Send it by email. The PDF is attached and the customer gets a link to view and pay it online.");
  await guide.click("Email");
  const email = guide.dialog();
  await expect(guide.field("To", email)).toHaveValue(customers.others[0].email);
  await guide.click("Send", email);
  await guide.say("Every email sent is kept in Settings, Email log.");

  // ----- customer portal -----
  await page.getByRole("button", { name: "Share link" }).hover();
  await guide.say("Share link copies the customer's own web page for this invoice. Here's what the customer sees:");
  const share = await guide.api<{ url: string }>("POST", "/invoices/" + invoiceId + "/share-link");
  await guide.open(share.url);
  await expect(page.getByText(customers.others[0].display_name).first()).toBeVisible();
  await guide.say("The customer can download the PDF here, and pay online once a payment provider is connected.");
  await page.goBack();
  await guide.settle();

  // ----- receive payment -----
  await guide.say("When the customer pays, click Receive payment.");
  await guide.clickLink("Receive payment");
  await guide.choose("Payment method", "Check");
  await guide.type("Reference no.", "1045");
  await expect(main.locator('tbody input[type="checkbox"]').first()).toBeChecked();
  await guide.say("The invoice is already ticked with its full balance. Money goes to Undeposited Funds until you deposit it.");
  await guide.click("Save payment");
  await page.waitForURL(/\/sales\/payments$/);
  await guide.settle();

  await guide.open("/sales/invoices/" + invoiceId);
  await guide.expectText(/Paid/);
  await guide.say("The invoice is now marked Paid.");

  // ----- sales receipt -----
  await guide.newMenu("Sales receipt");
  await guide.say("A sales receipt is for a sale paid on the spot - no invoice needed.");
  await guide.choose("Customer", customers.others[1].display_name);
  await guide.fillLine(0, products.others[2].name, "3");
  await guide.choose("Payment method", "Cash");
  await guide.click("Save sales receipt");
  await page.waitForURL(/\/sales\/forms\/sales-receipts\/\d+$/);
  await guide.settle();

  // ----- credit memo -----
  await guide.newMenu("Credit memo");
  await guide.say("A credit memo gives a customer credit, for example for a missed visit. It is used up by their next payment.");
  await guide.choose("Customer", customers.main.display_name);
  await guide.fillLine(0, products.service.name, "1");
  await guide.click("Save credit memo");
  await page.waitForURL(/\/sales\/forms\/credit-memos\/\d+$/);
  await guide.settle();

  // ----- refund receipt -----
  await guide.newMenu("Refund receipt");
  await guide.say("A refund receipt records money you gave back to a customer.");
  await guide.choose("Customer", customers.others[1].display_name);
  await guide.choose("Refund from", /Checking/);
  await guide.choose("Payment method", "Cash");
  await guide.fillLine(0, products.others[2].name, "1");
  await guide.click("Save refund receipt");
  await page.waitForURL(/\/sales\/forms\/refund-receipts\/\d+$/);
  await guide.settle();

  // ----- delayed charge -----
  await guide.newMenu("Delayed charge");
  await guide.say("A delayed charge records work to bill later. It's added to the customer's next invoice for you.");
  await guide.choose("Customer", customers.others[2].display_name);
  await guide.fillLine(0, products.others[0].name, "2");
  await guide.click("Save delayed charge");
  await page.waitForURL(/\/sales\/forms\/delayed-charges\/\d+$/);
  await guide.settle();

  // ----- customer page and statements -----
  await guide.nav("Sales", "Customers");
  await main.getByText(customers.main.display_name, { exact: true }).first().click();
  await page.waitForURL(/\/sales\/customers\/\d+$/);
  await guide.settle();
  await guide.say("Each customer has a page with their open balance, every transaction, and statements you can print or email.");
  await guide.scrollPage(500);
  await guide.scrollPage(-500);

  // ----- invoice list, reminders -----
  await guide.nav("Sales", "Invoices");
  await guide.say("The invoice list shows what's open, paid and overdue. Late fees and reminders can also be run by hand from here.");
  await guide.click("Send reminders");
  await expect(main).toBeVisible();
}
