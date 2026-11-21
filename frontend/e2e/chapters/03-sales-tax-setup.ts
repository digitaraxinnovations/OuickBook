import { tax } from "../demo-data";
import { DemoGuide } from "../support/DemoGuide";
import { appConfig } from "../../src/config/app.config";

/** The tax agency and rate used on the invoices that follow. */
export async function salesTaxSetup(guide: DemoGuide): Promise<void> {
  await guide.chapter("Sales tax setup", `Tell ${appConfig.appName} who you collect tax for and how much`);

  await guide.nav("Taxes", "Sales tax");
  await guide.say(`Before sending invoices, set up sales tax. ${appConfig.appName} then works out what you owe each agency.`);
  await guide.clickLink("Set up sales tax");

  await guide.click("Add agency");
  let dialog = guide.dialog();
  await guide.type("Agency name", tax.agency, dialog);
  await guide.choose("Filing frequency", "Quarterly", dialog);
  await guide.say("The filing frequency sets the periods you file and pay in.");
  await guide.click("Save", dialog);
  await guide.expectText(tax.agency);

  await guide.click("Add rate");
  dialog = guide.dialog();
  await guide.type("Rate name", tax.rateName, dialog);
  await guide.type("Rate (%)", tax.rate, dialog);
  await guide.say("Saving the rate also creates a tax code you can pick on invoices. Several rates can be combined into one code.");
  await guide.click("Save", dialog);
  await guide.expectText(tax.rateName);
}
