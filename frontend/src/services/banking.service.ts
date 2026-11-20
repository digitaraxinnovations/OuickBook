import { ApiClient } from "@/lib/api-client";
import { AddBankLineInput, BankRuleInput, StatementImportInput, TransferInput } from "@/types/inputs";
import {
  BankAccountOverview,
  BankRule,
  BankTransaction,
  BankTransactionStatus,
  DiscrepancyItem,
  MatchCandidate,
  Reconciliation,
  ReconciliationReport,
  ReconciliationWorkspace,
  StatementImportResult,
  Transfer,
} from "@/types/models";

/** Everything on the Banking pages: transfers, review queue, rules and reconciliation. */
export class BankingService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  // ----- overview & transfers -----

  accounts(): Promise<BankAccountOverview[]> {
    return this.api.get<BankAccountOverview[]>("/banking/accounts");
  }

  transfers(): Promise<Transfer[]> {
    return this.api.get<Transfer[]>("/banking/transfers");
  }

  createTransfer(input: TransferInput): Promise<Transfer> {
    return this.api.post<Transfer>("/banking/transfers", input);
  }

  voidTransfer(id: number): Promise<Transfer> {
    return this.api.post<Transfer>("/banking/transfers/" + id + "/void");
  }

  // ----- importing -----

  importStatement(input: StatementImportInput): Promise<StatementImportResult> {
    return this.api.post<StatementImportResult>("/banking/import", input);
  }

  syncFeed(accountId: number): Promise<StatementImportResult> {
    return this.api.post<StatementImportResult>("/banking/accounts/" + accountId + "/sync");
  }

  applyRules(accountId: number): Promise<{ count: number }> {
    return this.api.post("/banking/apply-rules?account_id=" + accountId);
  }

  // ----- review queue -----

  transactions(accountId: number, status: BankTransactionStatus): Promise<BankTransaction[]> {
    return this.api.get<BankTransaction[]>("/banking/transactions", { account_id: accountId, status: status });
  }

  matches(id: number): Promise<MatchCandidate[]> {
    return this.api.get<MatchCandidate[]>("/banking/transactions/" + id + "/matches");
  }

  match(id: number, journalLineId: number): Promise<BankTransaction> {
    return this.api.post<BankTransaction>("/banking/transactions/" + id + "/match", { journal_line_id: journalLineId });
  }

  add(id: number, input: AddBankLineInput): Promise<BankTransaction> {
    return this.api.post<BankTransaction>("/banking/transactions/" + id + "/add", input);
  }

  exclude(id: number): Promise<BankTransaction> {
    return this.api.post<BankTransaction>("/banking/transactions/" + id + "/exclude");
  }

  undo(id: number): Promise<BankTransaction> {
    return this.api.post<BankTransaction>("/banking/transactions/" + id + "/undo");
  }

  // ----- rules -----

  rules(): Promise<BankRule[]> {
    return this.api.get<BankRule[]>("/banking/rules");
  }

  createRule(input: BankRuleInput): Promise<BankRule> {
    return this.api.post<BankRule>("/banking/rules", input);
  }

  updateRule(id: number, input: BankRuleInput): Promise<BankRule> {
    return this.api.put<BankRule>("/banking/rules/" + id, input);
  }

  deleteRule(id: number): Promise<void> {
    return this.api.delete<void>("/banking/rules/" + id);
  }

  // ----- reconciliation -----

  reconciliations(accountId: number): Promise<Reconciliation[]> {
    return this.api.get<Reconciliation[]>("/banking/reconciliations", { account_id: accountId });
  }

  startReconciliation(accountId: number, statementDate: string, endingBalance: string): Promise<Reconciliation> {
    return this.api.post<Reconciliation>("/banking/reconciliations", {
      account_id: accountId,
      statement_date: statementDate,
      ending_balance: endingBalance,
    });
  }

  workspace(id: number): Promise<ReconciliationWorkspace> {
    return this.api.get<ReconciliationWorkspace>("/banking/reconciliations/" + id);
  }

  saveSelection(id: number, lineIds: number[]): Promise<ReconciliationWorkspace> {
    return this.api.put<ReconciliationWorkspace>("/banking/reconciliations/" + id + "/selection", { journal_line_ids: lineIds });
  }

  finish(id: number): Promise<Reconciliation> {
    return this.api.post<Reconciliation>("/banking/reconciliations/" + id + "/finish");
  }

  undoReconciliation(id: number): Promise<Reconciliation> {
    return this.api.post<Reconciliation>("/banking/reconciliations/" + id + "/undo");
  }

  cancelReconciliation(id: number): Promise<void> {
    return this.api.delete<void>("/banking/reconciliations/" + id);
  }

  report(id: number): Promise<ReconciliationReport> {
    return this.api.get<ReconciliationReport>("/banking/reconciliations/" + id + "/report");
  }

  discrepancies(accountId: number): Promise<DiscrepancyItem[]> {
    return this.api.get<DiscrepancyItem[]>("/banking/reconciliations/discrepancies", { account_id: accountId });
  }
}
