import React from 'react';
import { VerticalLanding } from '../components/VerticalLanding';
import { MarketingChatWidget } from '../components/MarketingChatWidget';

export const MedicalLanding: React.FC = () => {
  return (
    <>
    <VerticalLanding
      industry="medical practice"
      title="HIPAA-Compliant Medical Practice Automation"
      subtitle="HIPAA-compliant reminders, appointment confirmations, and patient intake automation that reduces no-shows and improves patient care."
      icon="🏥"
      painPoints={[
        "High no-show rates wasting valuable appointment slots",
        "Manual patient intake forms taking up appointment time",
        "HIPAA compliance concerns with patient communication",
        "Staff spending hours on appointment confirmations",
        "No system to track patient preferences and history",
        "Missed follow-up appointments and care gaps"
      ]}
      solutions={[
        "HIPAA-compliant automated reminders reduce no-shows by 40%",
        "Digital patient intake forms save 15 minutes per appointment",
        "Secure patient communication meets all HIPAA requirements",
        "Staff focus on patient care while AI handles scheduling",
        "Patient preference tracking improves care quality",
        "Automated follow-up scheduling ensures continuity of care"
      ]}
      workflows={[
        "Appointment scheduled → HIPAA-compliant confirmation sent → Patient preferences recorded",
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
          "HIPAA-compliant communication",
          "Automated appointment reminders",
          "Digital patient intake",
          "Care plan management",
          "Prescription tracking",
          "Compliance reporting"
        ]
      }}
      testimonials={[
        {
          name: "Dr. Jennifer Martinez",
          business: "Martinez Family Practice",
          quote: "Our no-show rate dropped from 25% to 8% with Fikiri's automated reminders. We're seeing 20% more patients."
        },
        {
          name: "Dr. Robert Kim",
          business: "Kim Cardiology Clinic",
          quote: "The HIPAA-compliant system gives us peace of mind. Patient satisfaction scores increased significantly."
        },
        {
          name: "Dr. Sarah Johnson",
          business: "Johnson Pediatrics",
          quote: "Digital intake forms save us 2 hours daily. Parents love the convenience, and we love the efficiency."
        }
      ]}
      ctaText="Ensure HIPAA Compliance"
      ctaLink="/signup?industry=medical"
    />
    <MarketingChatWidget />
    </>
  );
};
