"use client";

import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { inventoryService } from "@/services";
import { Product, StockMovement } from "@/types/models";

interface HistoryRow extends StockMovement {
  onHand: number;
}

/** Adds a running "on hand" column to the stock movements. */
function withRunningQuantity(movements: StockMovement[]): HistoryRow[] {
  let onHand = 0;
  return movements.map((movement) => {
    onHand += toNumber(movement.quantity);
    return { ...movement, onHand: onHand };
  });
}

interface StockHistoryDialogProps {
  product: Product;
  currency?: string;
  onClose: () => void;
}

export function StockHistoryDialog({ product, currency, onClose }: StockHistoryDialogProps) {
  const history = useLoad(() => inventoryService.stockHistory(product.id), [product.id]);
  const rows = withRunningQuantity(history.data || []);

  return (
    <Modal title={"Stock history - " + product.name} open={true} onClose={onClose} wide>
      <ErrorMessage message={history.error} />
      {history.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={rows.slice().reverse()}
          rowKey={(row) => row.id}
          emptyText="No stock movements yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.movement_date) },
            { header: "Transaction", render: (row) => row.description },
            { header: "Qty", align: "right", render: (row) => (toNumber(row.quantity) > 0 ? "+" : "") + toNumber(row.quantity) },
            { header: "Value", align: "right", render: (row) => formatMoney(row.value, currency) },
            { header: "On hand", align: "right", render: (row) => row.onHand },
          ]}
        />
      )}
    </Modal>
  );
}
