import { expect } from "@playwright/test";
import { customers, employees, products } from "../demo-data";
import { isoDate } from "../support/dates";
import { DemoGuide } from "../support/DemoGuide";

/** Pay schedules and pay items, employees, timesheets, running payroll and paying liabilities. */
export async function payroll(guide: DemoGuide): Promise<void> {
  const { page } = guide;
  const main = page.locator("main");

  await guide.chapter("Payroll and time", "Pay your team and track the hours they work");

  // ----- settings: schedule and pay items -----
  await guide.nav("Payroll", "Payroll settings");
  await guide.say("Payroll starts with a pay schedule: how often people are paid.");
  await guide.click("Add schedule");
  let dialog = guide.dialog("Pay schedule");
  await guide.type("Name", "Every other Friday", dialog);
  await guide.choose("How often", "Every other week", dialog);
  await guide.setDate("End of the next pay period", isoDate(5), dialog);
  await guide.setDate("Next pay day", isoDate(7), dialog);
  await guide.click("Save", dialog);
  await guide.expectText("Every other Friday");

  await guide.say("Pay items are everything on a paycheck besides regular pay: taxes withheld, deductions and employer costs.");
  await guide.click("Add pay item");
  dialog = guide.dialog("Pay item");
  await guide.type("Name", "Federal income tax", dialog);
  await guide.choose("Kind", "Employee tax (withheld)", dialog);
  await guide.choose("Usual amount", "Percent of gross pay", dialog);
  await guide.type("Percent", "10", dialog);
  await guide.click("Save", dialog);
  await guide.expectText("Federal income tax");

  await guide.click("Add pay item");
  dialog = guide.dialog("Pay item");
  await guide.type("Name", "Employer social security", dialog);
  await guide.choose("Kind", "Employer tax", dialog);
  await guide.choose("Usual amount", "Percent of gross pay", dialog);
  await guide.type("Percent", "6.2", dialog);
  await guide.click("Save", dialog);
  await guide.expectText("Employer social security");

  // ----- employees -----
  await guide.nav("Payroll", "Employees");
  await guide.say("Add each employee with their pay type, rate and schedule.");
  await guide.click("Add employee");
  dialog = guide.dialog("New employee");
  await guide.type("Name", employees.hourly.name, dialog);
  await guide.type("Email", employees.hourly.email, dialog);
  await guide.setDate("Hire date", isoDate(-90), dialog);
  await guide.choose("Pay schedule", "Every other Friday", dialog);
  await guide.choose("Pay type", "Hourly", dialog);
  await guide.type("Rate per hour", employees.hourly.rate, dialog);
  await guide.type("Usual hours per pay period", employees.hourly.hours, dialog);
  await guide.choose("Paid by", "Direct deposit", dialog);
  await guide.say("Taxes and deductions from the pay items are added to every paycheck.");
  await guide.click("Add pay item", dialog);
  await guide.chooseIn(dialog.locator("select", { has: page.locator("option", { hasText: "Choose a pay item" }) }).last(), /^Federal income tax/);
  await guide.click("Add pay item", dialog);
  await guide.chooseIn(dialog.locator("select", { has: page.locator("option", { hasText: "Choose a pay item" }) }).last(), /^Employer social security/);
  await guide.click("Save", dialog);
  await guide.expectText(employees.hourly.name);

  await guide.click("Add employee");
  dialog = guide.dialog("New employee");
  await guide.type("Name", employees.salaried.name, dialog);
  await guide.type("Email", employees.salaried.email, dialog);
  await guide.choose("Pay schedule", "Every other Friday", dialog);
  await guide.choose("Pay type", "Salary", dialog);
  await guide.type("Salary per year", "62400", dialog);
  await guide.choose("Paid by", "Paper check", dialog);
  await guide.click("Save", dialog);
  await guide.expectText(employees.salaried.name);

  // ----- time -----
  await guide.nav("Payroll", "Time");
  await guide.say("The weekly timesheet records hours worked. Billable hours can go straight onto the customer's next invoice.");
  await guide.chooseIn(main.locator("select", { has: page.locator("option", { hasText: "Who did the work?" }) }).first(), employees.hourly.name);
  const row = main.locator("table tbody tr").first();
  await guide.chooseIn(row.locator("select").first(), customers.main.display_name);
  await guide.chooseIn(row.locator("select").last(), products.others[0].name);
  await row.getByRole("checkbox", { name: "Billable" }).check();
  for (const day of ["Mon", "Tue", "Wed"]) {
    await guide.typeInto(row.getByRole("spinbutton", { name: day + " hours" }), "6");
  }
  await guide.click("Save timesheet");
  await guide.expectText(/18/);

  // ----- run payroll -----
  await guide.nav("Payroll", "Run payroll");
  await guide.say("Run payroll for a pay period. Ledgerly works out every paycheck from salaries, hours and pay items.");
  await guide.click("Run payroll");
  dialog = guide.dialog();
  await guide.choose("Pay schedule", "Every other Friday", dialog);
  await guide.choose("Pay from", /Checking/, dialog);
  await guide.click("Continue", dialog);
  await page.waitForURL(/\/payroll\/runs\/\d+$/);
  await guide.settle();
  await guide.say("Check the paychecks. Click one to change hours or amounts before approving.");
  await guide.scrollPage(400);
  await guide.click("Approve payroll");
  await expect(main.getByText(/Approved|Paid/i).first()).toBeVisible();
  await guide.say("Approved: pay is recorded in the books and pay stubs are ready to print.");

  // ----- liabilities -----
  await guide.nav("Payroll", "Payroll liabilities");
  await guide.say("Taxes withheld and employer taxes are owed to the government until you pay them. Record those payments here.");
  await main.getByRole("button", { name: "Pay", exact: true }).first().click();
  dialog = guide.dialog();
  await guide.choose("Pay from", /Checking/, dialog);
  await guide.type("Memo", "Federal tax deposit", dialog);
  await guide.click("Record payment", dialog);
  await guide.settle();
}
