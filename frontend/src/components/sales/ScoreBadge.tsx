import { PaymentScore, ScoreRating } from "@/types/models";

const looks: Record<ScoreRating, { label: string; color: string }> = {
  GOOD: { label: "Good", color: "bg-green-100 text-green-800" },
  WATCH: { label: "Watch", color: "bg-amber-100 text-amber-800" },
  RISKY: { label: "Risky", color: "bg-red-100 text-red-700" },
  NOT_ENOUGH_HISTORY: { label: "Not enough history", color: "bg-gray-100 text-gray-600" },
};

/** How reliably a customer pays. Hover shows the reason. */
export function ScoreBadge({ score }: { score: PaymentScore }) {
  const look = looks[score.rating];
  return (
    <span title={score.reason} className={"whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold " + look.color}>
      {look.label}
    </span>
  );
}

/** The badge with the reason and what to do about it. */
export function ScoreNote({ score }: { score: PaymentScore }) {
  return (
    <div className="text-sm">
      <ScoreBadge score={score} />
      <span className="ml-2 text-gray-700">{score.reason}</span>
      <div className="mt-1 text-gray-500">{score.suggestion}</div>
    </div>
  );
}
