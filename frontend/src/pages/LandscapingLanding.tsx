import React from 'react';
import { VerticalLanding } from '../components/VerticalLanding';
import { MarketingChatWidget } from '../components/MarketingChatWidget';

export const LandscapingLanding: React.FC = () => {
  return (
    <>
    <VerticalLanding
      industry="landscaping"
      title="Landscaping Business Automation"
      subtitle="Never lose track of a client again. Automated scheduling, weather-based rescheduling, and project estimates that close more deals."
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
        "Weather-based automatic rescheduling keeps your calendar accurate",
        "Client history tracking remembers preferences and past projects",
        "AI-generated estimates that match your pricing and close deals",
        "Automated reminders keep clients engaged and reduce no-shows",
        "Smart scheduling prevents conflicts and optimizes your routes",
        "Seasonal planning automation ensures recurring revenue"
      ]}
      workflows={[
        "Client calls → AI captures details → Schedules estimate visit",
        "Weather forecast changes → Automatic rescheduling → Client notification",
        "Estimate visit → Photos uploaded → AI generates professional quote",
        "Quote approved → Project scheduled → Materials ordered automatically",
        "Project completed → Follow-up scheduled → Next service planned",
        "Seasonal reminder → Client contacted → Service booked"
      ]}
      pricing={{
        tier: "Professional",
        price: 99,
        features: [
          "Unlimited client management",
          "Weather-based scheduling",
          "AI-powered estimates",
          "Automated reminders",
          "Route optimization",
          "Seasonal planning"
        ]
      }}
      testimonials={[
        {
          name: "Mike Rodriguez",
          business: "Rodriguez Landscaping",
          quote: "Fikiri Solutions saved me 15 hours per week on scheduling and estimates. My revenue increased 40% in the first quarter."
        },
        {
          name: "Sarah Chen",
          business: "Green Thumb Landscaping",
          quote: "The weather-based rescheduling feature is a game-changer. No more angry clients or wasted trips."
        },
        {
          name: "David Thompson",
          business: "Thompson Lawn Care",
          quote: "The AI estimates are so accurate, my close rate went from 30% to 75%. It's like having a sales expert on my team."
        }
      ]}
      ctaText="Start Your Free Trial"
      ctaLink="/signup?industry=landscaping"
    />
    <MarketingChatWidget />
    </>
  );
};
