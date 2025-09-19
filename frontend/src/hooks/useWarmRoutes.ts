import { useEffect } from "react";

export function useWarmRoutes() {
  useEffect(() => {
    // start fetching after first paint
    const t = setTimeout(() => {
      import("../pages/EnhancedDashboard");
      import("../pages/CompactDashboard");
      import("../components/DashboardCharts");
    }, 1200);
    return () => clearTimeout(t);
  }, []);
}
