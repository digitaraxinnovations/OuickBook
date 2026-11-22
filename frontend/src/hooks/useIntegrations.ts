"use client";

import { useLoad } from "@/hooks/useLoad";
import { platformService } from "@/services";
import { Integrations } from "@/types/models";

/** Which outside services are connected; null while loading or when the user may not see it. */
export function useIntegrations(): Integrations | null {
  const status = useLoad(() => platformService.integrations());
  return status.data || null;
}
