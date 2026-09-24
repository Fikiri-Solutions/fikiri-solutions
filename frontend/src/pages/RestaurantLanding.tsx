import React from 'react';
import { VerticalLanding } from '../components/VerticalLanding';
import { MarketingChatWidget } from '../components/MarketingChatWidget';
import { PageMeta } from '../components/PageMeta';

export const RestaurantLanding: React.FC = () => {
  return (
    <>
    <PageMeta route="/industries/restaurant" />
    <VerticalLanding
      industry="restaurant"
      title="Restaurant Automation Platform"
      subtitle="Automated reservations, guest communication, and loyalty follow-up so your team can stay focused on service."
      icon="🍽️"
      painPoints={[
        "Manual reservation management leads to double-bookings",
        "No system to track customer preferences and dietary restrictions",
        "Missing opportunities to follow up after visits",
        "Loyalty programs that customers forget to use",
        "Staff spending time on phone calls instead of service",
        "No structured view of guest communication history"
      ]}
      solutions={[
        "Reservation capture and confirmation workflows that reduce double-booking risk",
        "Preference tracking to support personalized menu and visit notes",
        "Follow-up messages that prompt return visits without manual chasing",
        "Loyalty program reminders and status updates",
        "Staff focus on service while automation handles routine guest messages",
        "Guest communication history for clearer handoffs between shifts"
      ]}
      workflows={[
        "Customer calls → AI captures reservation → Table assigned → Confirmation sent",
        "Customer arrives → Preferences loaded → Staff notes available",
        "Order placed → Follow-up preferences recorded → Loyalty points updated",
        "Meal completed → Feedback requested → Next visit suggested",
        "Loyalty points earned → Reward notification → Return visit booked",
        "Slow period detected → Promotional offers sent → Tables filled"
      ]}
      pricing={{
        tier: "Business",
        price: 199,
        features: [
          "Reservation and confirmation workflows",
          "Customer preference tracking",
          "Menu and visit communication helpers",
          "Loyalty program automation",
          "Follow-up messaging",
          "Guest communication history"
        ]
      }}
      engagementCategories={[
        "Reservation capture and confirmations",
        "Guest preference and dietary notes",
        "Loyalty reminders and return-visit follow-up",
        "Shift handoff communication history",
        "Promotional and slow-period outreach",
        "Workflow consulting for front-of-house operations"
      ]}
      ctaText="Improve Restaurant Follow-Up"
      ctaLink="/signup?industry=restaurant"
    />
    <MarketingChatWidget />
    </>
  );
};
