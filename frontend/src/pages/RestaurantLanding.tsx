import React from 'react';
import { VerticalLanding } from '../components/VerticalLanding';
import { PublicChatbotWidget } from '../components/PublicChatbotWidget';

export const RestaurantLanding: React.FC = () => {
  return (
    <>
    <VerticalLanding
      industry="restaurant"
      title="Restaurant Automation Platform"
      subtitle="Turn every customer interaction into revenue. Automated reservations, menu recommendations, and loyalty programs that keep customers coming back."
      icon="🍽️"
      painPoints={[
        "Manual reservation management leads to double-bookings",
        "No system to track customer preferences and dietary restrictions",
        "Missing opportunities to upsell and increase average order value",
        "Loyalty programs that customers forget to use",
        "Staff spending time on phone calls instead of service",
        "No data on customer behavior and preferences"
      ]}
      solutions={[
        "Smart reservation system prevents double-bookings and optimizes seating",
        "Customer preference tracking enables personalized menu recommendations",
        "AI-powered upselling increases average order value by 25%",
        "Automated loyalty program management increases repeat visits",
        "Staff focus on service while AI handles customer communication",
        "Customer analytics provide insights for menu and service improvements"
      ]}
      workflows={[
        "Customer calls → AI captures reservation → Table assigned → Confirmation sent",
        "Customer arrives → Preferences loaded → Personalized menu suggested",
        "Order placed → AI suggests upsells → Bill optimized → Loyalty points added",
        "Meal completed → Feedback requested → Next visit scheduled",
        "Loyalty points earned → Reward notification → Return visit booked",
        "Slow period detected → Promotional offers sent → Tables filled"
      ]}
      pricing={{
        tier: "Premium",
        price: 249,
        features: [
          "Unlimited reservations",
          "Customer preference tracking",
          "AI menu recommendations",
          "Loyalty program automation",
          "Upselling optimization",
          "Customer analytics dashboard"
        ]
      }}
      testimonials={[
        {
          name: "Maria Santos",
          business: "Santos Family Restaurant",
          quote: "Our average order value increased 30% with Fikiri's upselling suggestions. Customers love the personalized recommendations."
        },
        {
          name: "James Wilson",
          business: "Wilson's Bistro",
          quote: "The reservation system eliminated our double-booking problems completely. Our staff can focus on what they do best."
        },
        {
          name: "Lisa Park",
          business: "Park's Korean Kitchen",
          quote: "Customer retention increased 50% with the automated loyalty program. Our regulars feel truly valued."
        }
      ]}
      ctaText="Boost Your Restaurant Revenue"
      ctaLink="/signup?industry=restaurant"
    />
    <PublicChatbotWidget />
    </>
  );
};
