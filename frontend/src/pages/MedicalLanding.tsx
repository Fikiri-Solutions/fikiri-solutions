import React from 'react';
import { VerticalLanding } from '../components/VerticalLanding';
import { MarketingChatWidget } from '../components/MarketingChatWidget';
import { PageMeta } from '../components/PageMeta';

export const MedicalLanding: React.FC = () => {
  return (
    <>
    <PageMeta route="/industries/medical" />
    <VerticalLanding
      industry="medical practice"
      title="Medical Practice Workflow Automation"
      subtitle="Appointment reminders, confirmations, and intake follow-up designed for secure, privacy-aware practice operations."
      icon="🏥"
      painPoints={[
        "High no-show rates wasting valuable appointment slots",
        "Manual patient intake forms taking up appointment time",
        "Staff concern about how patient communication is handled",
        "Staff spending hours on appointment confirmations",
        "No system to track patient preferences and history",
        "Missed follow-up appointments and care gaps"
      ]}
      solutions={[
        "Automated reminders and confirmations to reduce no-shows",
        "Digital intake workflows that save time before appointments",
        "Role-based access and encrypted transport for practice data",
        "Staff focus on patient care while automation handles scheduling messages",
        "Preference tracking to personalize follow-up communication",
        "Automated follow-up scheduling to support continuity of care"
      ]}
      workflows={[
        "Appointment scheduled → Confirmation sent → Preferences recorded",
        "48 hours before → Reminder sent → Confirmation requested → Preferences updated",
        "Patient arrives → Intake form pre-filled → Appointment optimized → Care plan updated",
        "Appointment completed → Follow-up scheduled → Care instructions sent",
        "Prescription needed → Pharmacy contacted → Patient notified → Refill reminders set",
        "Annual checkup due → Patient contacted → Appointment scheduled → Preventive care planned"
      ]}
      pricing={{
        tier: "Enterprise",
        price: 499,
        features: [
          "Privacy-aware messaging workflows",
          "Automated appointment reminders",
          "Digital patient intake",
          "Care plan management",
          "Prescription tracking",
          "Operational reporting"
        ]
      }}
      engagementCategories={[
        "Appointment reminders and confirmations",
        "Digital intake and preference capture",
        "Follow-up and continuity messaging",
        "Staff workload reduction for front-desk tasks",
        "Secure account access with role-based controls",
        "Workflow consulting for practice operations"
      ]}
      ctaText="Start a Practice Workflow Conversation"
      ctaLink="/intake"
    />
    <MarketingChatWidget />
    </>
  );
};
