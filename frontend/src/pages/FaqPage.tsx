import React from 'react'
import { Link } from 'react-router-dom'
import { RadiantLayout, Container, Gradient, AnimatedBackground } from '../components/radiant'
import { PublicChatbotWidget } from '../components/PublicChatbotWidget'
import { ArrowRight } from 'lucide-react'

/** Pricing & product FAQs (moved from /pricing). */
export const PRICING_FAQ_ITEMS = [
  {
    question: 'Which plan is right for me?',
    answer:
      'We help businesses of all sizes save money through automation. Starter is great for small businesses getting started. Growth fits teams that need more automation and higher limits. Business is for established companies, and Enterprise is for large organizations with custom needs.',
  },
  {
    question: 'Can I change plans anytime?',
    answer:
      "Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any billing differences.",
  },
  {
    question: 'Do you offer a free trial?',
    answer: 'Yes, all plans come with a 7-day free trial. No credit card required to get started.',
  },
  {
    question: 'What happens if I exceed my response limit?',
    answer:
      "We'll notify you when you're approaching your limit. You can upgrade your plan or purchase additional responses as needed.",
  },
  {
    question: 'Are all automation actions production-complete today?',
    answer:
      'No. Core automation paths are live now. Some advanced actions are marked as partial or coming soon in Automation Studio so teams can plan safely.',
  },
] as const

const FaqPage: React.FC = () => {
  return (
    <RadiantLayout>
      <div className="min-h-screen bg-background text-foreground overflow-hidden relative">
        <div className="absolute inset-0 fikiri-gradient-animated pointer-events-none">
          <AnimatedBackground />
        </div>
        <div className="relative z-10">
          <section className="relative py-16 sm:py-20 z-10">
            <Container>
              <div className="max-w-4xl mx-auto text-center">
                <h1 className="text-4xl sm:text-5xl font-bold mb-4 text-foreground">
                  Frequently asked questions
                </h1>
                <p className="text-lg text-muted-foreground mb-8">
                  Billing, plans, and how Fikiri fits your team.
                </p>
                <Link
                  to="/pricing"
                  className="inline-flex items-center gap-2 text-sm font-medium text-brand-primary hover:text-brand-secondary"
                >
                  View pricing &amp; plans
                  <ArrowRight className="w-4 h-4" aria-hidden />
                </Link>
              </div>
            </Container>
          </section>

          <section className="relative pb-20 bg-muted/50 z-10">
            <Container>
              <div className="max-w-4xl mx-auto">
                <div className="space-y-6">
                  {PRICING_FAQ_ITEMS.map((faq, index) => (
                    <div
                      key={index}
                      className="bg-card/90 backdrop-blur-sm rounded-xl p-6 border border-border shadow-sm"
                    >
                      <h2 className="text-lg font-semibold text-foreground mb-3">{faq.question}</h2>
                      <p className="text-muted-foreground">{faq.answer}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Container>
          </section>

          <section className="relative py-16 z-10">
            <Gradient className="absolute inset-0 opacity-20" />
            <Container className="relative">
              <div className="max-w-4xl mx-auto text-center">
                <p className="text-muted-foreground mb-4">Still deciding?</p>
                <Link
                  to="/pricing"
                  className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-brand-primary hover:bg-fikiri-400 text-white font-semibold rounded-full transition-all duration-300 shadow-md"
                >
                  Compare plans
                  <ArrowRight className="w-5 h-5" aria-hidden />
                </Link>
              </div>
            </Container>
          </section>
        </div>
      </div>
      <PublicChatbotWidget />
    </RadiantLayout>
  )
}

export default FaqPage
