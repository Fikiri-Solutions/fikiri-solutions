import { useEffect, useState } from "react";
import { apiClient } from "../services/apiClient";

interface TimeseriesData {
  day: string;
  leads: number;
  emails: number;
  revenue: number;
}

interface SummaryData {
  leads: {
    change_pct: number | null;
    positive: boolean;
  };
  emails: {
    change_pct: number | null;
    positive: boolean;
  };
  revenue: {
    change_pct: number | null;
    positive: boolean;
  };
}

export function useDashboardTimeseries() {
  const [data, setData] = useState<TimeseriesData[]>([]);
  const [summary, setSummary] = useState<SummaryData>({
    leads: { change_pct: null, positive: true },
    emails: { change_pct: null, positive: true },
    revenue: { change_pct: null, positive: true }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        
        const response = await apiClient.getDashboardTimeseries(1);
        
        if (response.success) {
          setData(response.data.timeseries);
          setSummary(response.data.summary);
        } else {
          throw new Error(response.error || 'Failed to fetch data');
        }
      } catch (err) {
        console.error("Failed to fetch timeseries:", err);
        setError(err instanceof Error ? err.message : "Failed to fetch data");
        
        // Fallback data for development
        setData([
          { day: "2024-01-01", leads: 5, emails: 12, revenue: 1500 },
          { day: "2024-01-02", leads: 8, emails: 18, revenue: 2200 },
          { day: "2024-01-03", leads: 12, emails: 25, revenue: 3100 },
          { day: "2024-01-04", leads: 7, emails: 15, revenue: 1800 },
          { day: "2024-01-05", leads: 15, emails: 32, revenue: 4200 },
          { day: "2024-01-06", leads: 9, emails: 21, revenue: 2600 },
          { day: "2024-01-07", leads: 11, emails: 28, revenue: 3400 }
        ]);
        setSummary({
          leads: { change_pct: 15.2, positive: true },
          emails: { change_pct: 8.7, positive: true },
          revenue: { change_pct: 22.1, positive: true }
        });
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return { data, summary, loading, error };
}
