"use client";

import { useEffect, useState } from "react";

/** True when the page URL has ?name=1 (used by the "+ New" menu to open a form). */
export function useQueryFlag(name: string): boolean {
  const [isSet, setIsSet] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setIsSet(params.get(name) === "1");
  }, [name]);

  return isSet;
}
