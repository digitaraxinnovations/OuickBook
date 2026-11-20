import { expect } from "@playwright/test";
import { customers, products } from "../demo-data";
import { DemoGuide } from "../support/DemoGuide";

/** Customers, products and services, categories, price rules and stock counts. */
export async function customersAndProducts(guide: DemoGuide): Promise<void> {
  const { page } = guide;

  await guide.chapter("Customers and products", "The people you sell to and the things you sell");

  // ----- customers -----
  await guide.nav("Sales", "Customers");
  await guide.say("Customers are the people and businesses you sell to. Let's add one.");
  await guide.click("New customer");
  const form = guide.dialog("New customer");
  await guide.type("Display name", customers.main.display_name, form);
  await guide.type("Company name", customers.main.company_name, form);
  await guide.type("Email", customers.main.email, form);
  await guide.type("Phone", customers.main.phone, form);
  await guide.type("Address", customers.main.address, form);
  await guide.choose("Payment terms", "Net 30", form);
  await guide.say("Each customer can have their own payment terms, sales tax rate and currency.");
  await guide.click("Save", form);
  await guide.expectText(customers.main.display_name);

  for (const customer of customers.others) {
    await guide.api("POST", "/customers", customer);
  }
  await page.reload();
  await guide.settle();
  await guide.say("We've added a few more customers the same way. The list shows each one's open balance.");
  await guide.expectText(customers.others[0].display_name);

  // ----- products and services -----
  await guide.nav("Sales", "Products & services");
  await guide.say("Products and services are what you sell. Picking one on an invoice fills in the description and price.");
  await guide.click("New item");
  let item = guide.dialog("New item");
  await guide.choose("Type", "Service", item);
  await guide.type("Name", products.service.name, item);
  await guide.type("Description (shown on invoices)", products.service.description, item);
  await guide.type("Sales price", products.service.price, item);
  await guide.click("Save", item);
  await guide.expectText(products.service.name);

  await guide.say("Inventory items also track how many you have on hand and what they cost you.");
  await guide.click("New item");
  item = guide.dialog("New item");
  await guide.choose("Type", "Inventory item (track quantity)", item);
  await guide.type("Name", products.inventory.name, item);
  await guide.type("SKU", products.inventory.sku, item);
  await guide.type("Description (shown on invoices)", products.inventory.description, item);
  await guide.type("Sales price", products.inventory.price, item);
  await guide.type("Cost", products.inventory.cost, item);
  await guide.type("Starting quantity", products.inventory.quantity, item);
  await guide.type("Reorder point", products.inventory.reorder, item);
  await guide.say("The reorder point warns you when stock runs low.");
  await guide.click("Save", item);
  await guide.expectText(products.inventory.name);

  for (const product of products.others) {
    await guide.api("POST", "/products", product);
  }
  await page.reload();
  await guide.settle();
  await guide.say("A few more services and products are added. You can also import and export the whole list as a spreadsheet.");

  // ----- categories and price rules -----
  await guide.nav("Sales", "Categories & price rules");
  await guide.say("Categories group your items. Price rules change prices for a sale or for special customers.");
  await guide.click("Add");
  let dialog = guide.dialog("Category");
  await guide.type("Name", products.category, dialog);
  await guide.click("Save", dialog);
  await guide.expectText(products.category);

  await guide.click("Add rule");
  dialog = guide.dialog("Price rule");
  await guide.type("Rule name", products.priceRule.name, dialog);
  await guide.choose("Change prices", "Lower by", dialog);
  await guide.type("Percent", products.priceRule.percent, dialog);
  await guide.choose("Applies to", "One item", dialog);
  await guide.choose("Item", products.service.name, dialog);
  await guide.say("This rule takes 10% off lawn mowing for everyone while it is active.");
  await guide.click("Save", dialog);
  await guide.expectText(products.priceRule.name);

  // ----- inventory adjustment -----
  await guide.nav("Sales", "Inventory adjustments");
  await guide.say("After a stock count, an inventory adjustment corrects the quantity on hand.");
  await guide.click("New adjustment");
  dialog = guide.dialog();
  const row = guide.lineRow(0, dialog);
  await guide.chooseIn(row.locator("select").first(), products.inventory.name);
  await guide.typeInto(row.locator("input").last(), "38");
  await guide.type("Memo", "Monthly stock count - 2 bags damaged", dialog);
  await guide.click("Save", dialog);
  await expect(page.locator("main").getByText(/stock count/i).first()).toBeVisible();
}
