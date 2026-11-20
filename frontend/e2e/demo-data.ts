/**
 * The made-up business used in the demo tour. Change names and amounts here;
 * the chapters only refer to these values.
 */

export const customers = {
  main: {
    display_name: "Amy's Bird Sanctuary",
    company_name: "Amy's Bird Sanctuary LLC",
    email: "amy@birds.example.com",
    phone: "(555) 201-3344",
    address: "4581 Finch Road\nSpringfield, IL 62704",
  },
  others: [
    { display_name: "Cool Cars", company_name: "Cool Cars Inc.", email: "office@coolcars.example.com", phone: "(555) 301-1188" },
    { display_name: "Diego Rodriguez", email: "diego@example.com", phone: "(555) 402-7781" },
    { display_name: "Freeman Sporting Goods", company_name: "Freeman Sporting Goods", email: "ap@freeman.example.com" },
  ],
  foreign: { display_name: "Maison Dupont", company_name: "Maison Dupont SARL", email: "compta@dupont.example.com" },
};

export const products = {
  service: { name: "Lawn mowing", description: "Weekly lawn mowing", price: "55.00" },
  inventory: { name: "Fertilizer bag", sku: "FERT-20", description: "20 kg slow-release fertilizer", price: "32.00", cost: "18.00", quantity: "40", reorder: "10" },
  others: [
    { name: "Hedge trimming", product_type: "SERVICE", sales_price: "75.00", description: "Hedge trimming, per hour" },
    { name: "Garden design", product_type: "SERVICE", sales_price: "120.00", description: "Garden design consultation" },
    { name: "Mulch (cubic yard)", product_type: "NON_INVENTORY", sales_price: "45.00", purchase_cost: "28.00" },
  ],
  category: "Lawn care",
  priceRule: { name: "Spring sale", percent: "10" },
};

export const vendors = {
  main: { display_name: "Green Supply Co", company_name: "Green Supply Co", email: "orders@greensupply.example.com", phone: "(555) 610-4400" },
  others: [
    { display_name: "City Power & Light", email: "billing@cpl.example.com" },
    { display_name: "Joe's Fuel Station" },
    { display_name: "Pat Turner (contractor)", email: "pat.turner@example.com" },
  ],
};

export const tax = {
  agency: "Illinois Department of Revenue",
  rateName: "Springfield sales tax",
  rate: "8.25",
};

export const employees = {
  hourly: { name: "Jordan Lee", email: "jordan@example.com", rate: "24.00", hours: "80" },
  salaried: { name: "Taylor Morgan", email: "taylor@example.com", salary: "2400.00" },
};

export const bank = {
  statementFile: "bank-statement.csv",
};

export const project = { name: "Sanctuary garden makeover" };

export const currency = { code: "EUR", rate: "1.08", paymentRate: "1.10" };

export const teammate = { email: "accountant@example.com", role: "Accountant" };
