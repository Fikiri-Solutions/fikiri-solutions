import { useEffect } from "react";

/**
 * After first paint, optionally warm the dashboard chunk for authenticated users.
 * Never warm chart/recharts modules on public visits — those load only when charts render.
 */
export function useWarmRoutes() {
  useEffect(() => {
    const t = setTimeout(() => {
      const hasSession =
        typeof window !== "undefined" &&
        !!localStorage.getItem("fikiri-user-id");
      if (!hasSession) return;
      void import("../pages/Dashboard");
    }, 1200);
    return () => clearTimeout(t);
  }, []);
}
