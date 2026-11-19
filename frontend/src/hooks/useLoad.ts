"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Loads data when a page opens and gives back loading / error state.
 *
 *   const customers = useLoad(() => customerService.list());
 *   customers.data, customers.loading, customers.error, customers.reload()
 */
export function useLoad<T>(loader: () => Promise<T>, dependencies: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(loader, dependencies);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await load();
      setData(result);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [load]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}
