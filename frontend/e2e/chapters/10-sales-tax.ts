import { tax } from "../demo-data";
import { DemoGuide } from "../support/DemoGuide";

/** What is owed to the tax agency, adjustments, and recording the payment. */
export async function salesTaxFiling(guide: DemoGuide): Promise<void> {
  await guide.chapter("Sales tax filing", "See what you owe, adjust it, and record the payment");

  await guide.nav("Taxes", "Sales tax");
  await guide.say("Every taxable sale added to what you owe the agency. This page shows the balance for each filing period.");

  await guide.click("Add adjustment");
  let dialog = guide.dialog();
  await guide.choose("Tax agency", tax.agency, dialog);
  await guide.choose("Type", "Decrease (you owe less)", dialog);
  await guide.type("Amount", "1.50", dialog);
  await guide.choose("Adjustment account", /Other Income/, dialog);
  await guide.type("Reason", "Discount for filing early", dialog);
  await guide.say("Adjustments handle corrections - here, the state's discount for filing early.");
  await guide.click("Save", dialog);
  await guide.expectText("Discount for filing early");

  await guide.click("Record payment");
  dialog = guide.dialog();
  await guide.say("When a filing period ends, choose it here and record the payment from your bank account. The current quarter is still open, so we'll stop here.");
  await guide.click("Cancel", dialog);
  await guide.say("The Sales Tax Liability report lists the taxable sales and tax for every period.");
}
