/** Marks a feature that runs on the built-in mock provider: it works, but nothing real happens. */
export function SimulatedBadge({ title = "Simulated: no real money moves and nothing is sent to an outside service." }: { title?: string }) {
  return (
    <span title={title} className="ml-1 whitespace-nowrap rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
      Simulated
    </span>
  );
}
