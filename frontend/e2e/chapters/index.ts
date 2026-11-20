import { DemoGuide } from "../support/DemoGuide";
import { gettingStarted } from "./01-getting-started";
import { customersAndProducts } from "./02-customers-products";
import { salesTaxSetup } from "./03-sales-tax-setup";
import { sales } from "./04-sales";
import { expenses } from "./05-expenses";
import { banking } from "./06-banking";
import { payroll } from "./07-payroll";
import { projectsAndTracking } from "./08-projects-tracking";
import { accounting } from "./09-accounting";
import { salesTaxFiling } from "./10-sales-tax";
import { reports } from "./11-reports";
import { multicurrency } from "./12-multicurrency";
import { companyAdmin } from "./13-company-admin";

export type Chapter = (guide: DemoGuide) => Promise<void>;

/** The tour, in order. Each chapter uses records made by the earlier ones. */
export const tourChapters: Chapter[] = [
  gettingStarted,
  customersAndProducts,
  salesTaxSetup,
  sales,
  expenses,
  banking,
  payroll,
  projectsAndTracking,
  accounting,
  salesTaxFiling,
  reports,
  multicurrency,
  companyAdmin,
];
