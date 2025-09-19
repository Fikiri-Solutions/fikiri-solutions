import { useState, useEffect } from 'react';

export type DashboardView = 'enhanced' | 'compact' | 'original';

const DASHBOARD_VIEW_KEY = 'fikiri_dashboard_view';

export function useDashboardView() {
  const [dashboardView, setDashboardView] = useState<DashboardView>('enhanced');

  // Load saved preference on mount
  useEffect(() => {
    const savedView = localStorage.getItem(DASHBOARD_VIEW_KEY) as DashboardView;
    if (savedView && ['enhanced', 'compact', 'original'].includes(savedView)) {
      setDashboardView(savedView);
    }
  }, []);

  // Save preference when changed
  const updateDashboardView = (view: DashboardView) => {
    setDashboardView(view);
    localStorage.setItem(DASHBOARD_VIEW_KEY, view);
    
    // Track analytics event
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'dashboard_view_changed', {
        view_type: view,
        timestamp: new Date().toISOString()
      });
    }
  };

  return {
    dashboardView,
    setDashboardView: updateDashboardView,
    isEnhanced: dashboardView === 'enhanced',
    isCompact: dashboardView === 'compact',
    isOriginal: dashboardView === 'original'
  };
}

