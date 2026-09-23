import React from 'react';
import { VerticalLanding } from '../components/VerticalLanding';
import { MarketingChatWidget } from '../components/MarketingChatWidget';
import { PageMeta } from '../components/PageMeta';

export const LandscapingLanding: React.FC = () => {
  return (
    <>
    <PageMeta route="/industries/landscaping" />
    <VerticalLanding
      industry="landscaping"
      title="Landscaping Business Automation"
      subtitle="Scheduling, weather-aware rescheduling, and estimate follow-up so you spend less time chasing clients."
      icon="🌱"
      painPoints={[
        "Missing appointments due to weather changes",
        "Losing track of client preferences and project history",
        "Spending hours on estimates that don't convert",
        "Clients forgetting about scheduled services",
        "Manual scheduling conflicts and double-bookings",
        "No system to track seasonal maintenance schedules"
      ]}
      solutions={[
        "Weather-aware rescheduling workflows that keep clients informed",
        "Client history tracking for preferences and past projects",
        "Estimate and quote follow-up that stays organized",
        "Automated reminders to reduce no-shows",
        "Scheduling helpers that surface conflicts earlier",
        "Seasonal planning reminders for recurring work"
      ]}
      workflows={[
        "Client calls → Details captured → Estimate visit scheduled",
        "Weather forecast changes → Rescheduling workflow → Client notification",
        "Estimate visit → Photos uploaded → Quote prepared",
        "Quote approved → Project scheduled → Materials checklist started",
        "Project completed → Follow-up scheduled → Next service planned",
        "Seasonal reminder → Client contacted → Service booked"
      ]}
      pricing={{
        tier: "Professional",
        price: 99,
        features: [
          "Unlimited client management",
          "Weather-aware scheduling workflows",
          "Estimate and quote follow-up",
          "Automated reminders",
          "Route and day planning helpers",
          "Seasonal planning reminders"
        ]
      }}
      engagementCategories={[
        "Scheduling and weather-aware rescheduling",
        "Estimate and quote follow-up",
        "Client history and preference tracking",
        "Seasonal maintenance reminders",
        "Route and day planning helpers",
        "Workflow consulting for field service operations"
      ]}
      ctaText="Start Your Free Trial"
      ctaLink="/signup?industry=landscaping"
    />
    <MarketingChatWidget />
    </>
  );
};
