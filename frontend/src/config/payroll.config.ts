/** Labels used on the payroll pages. */

export const frequencyOptions = [
  { value: "WEEKLY", label: "Every week" },
  { value: "BIWEEKLY", label: "Every other week" },
  { value: "SEMIMONTHLY", label: "Twice a month" },
  { value: "MONTHLY", label: "Every month" },
];

/** Pay item kinds you can add (regular, overtime and salary pay are built in). */
export const payItemKindOptions = [
  { value: "EARNING", label: "Extra earning (bonus, commission)" },
  { value: "DEDUCTION", label: "Deduction (retirement, health)" },
  { value: "EMPLOYEE_TAX", label: "Employee tax (withheld)" },
  { value: "EMPLOYER_TAX", label: "Employer tax" },
  { value: "EMPLOYER_CONTRIBUTION", label: "Employer contribution" },
];

export const payItemKindLabels: Record<string, string> = {
  REGULAR: "Regular pay",
  OVERTIME: "Overtime",
  SALARY: "Salary",
  EARNING: "Earning",
  DEDUCTION: "Deduction",
  EMPLOYEE_TAX: "Employee tax",
  EMPLOYER_TAX: "Employer tax",
  EMPLOYER_CONTRIBUTION: "Employer contribution",
};

export const payTypeOptions = [
  { value: "HOURLY", label: "Hourly" },
  { value: "SALARY", label: "Salary" },
];

export const paycheckMethodOptions = [
  { value: "CHECK", label: "Paper check" },
  { value: "DIRECT_DEPOSIT", label: "Direct deposit" },
];

/** Kinds that are taken off the paycheck or owed by the company until paid. */
export const liabilityKinds = ["DEDUCTION", "EMPLOYEE_TAX", "EMPLOYER_TAX", "EMPLOYER_CONTRIBUTION"];
