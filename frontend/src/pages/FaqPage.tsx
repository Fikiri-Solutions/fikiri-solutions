import React from 'react'
import { Link } from 'react-router-dom'
import { RadiantLayout, Container } from '../components/radiant'
import { MarketingChatWidget } from '../components/MarketingChatWidget'
import { PageMeta } from '../components/PageMeta'
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
      <PageMeta route="/faq" />
      <div className="relative min-h-dvh overflow-x-clip pb-[max(7rem,calc(env(safe-area-inset-bottom)+5.5rem))] sm:pb-[env(safe-area-inset-bottom)]">
        <div className="relative z-10">
          <section className="relative py-16 sm:py-20 z-10">
            <Container>
              <div className="max-w-4xl mx-auto text-center">
                <h1 className="mb-4 font-serif text-4xl font-bold text-white sm:text-5xl">
                  Frequently asked questions
                </h1>
                <p className="mb-8 font-serif text-lg text-white/65">
                  Billing, plans, and how Fikiri fits your team.
                </p>
                <Link
                  to="/pricing"
                  className="inline-flex items-center gap-2 text-sm font-medium text-orange-300 hover:text-orange-200"
                >
                  View pricing &amp; plans
                  <ArrowRight className="w-4 h-4" aria-hidden />
                </Link>
              </div>
            </Container>
          </section>

          <section className="relative pb-20 z-10">
            <Container>
              <div className="max-w-4xl mx-auto">
                <div className="space-y-6">
                  {PRICING_FAQ_ITEMS.map((faq, index) => (
                    <div
                      key={index}
                      className="bg-white/[0.95] backdrop-blur-sm rounded-xl p-6 border border-white/25 shadow-sm shadow-orange-950/15 font-serif"
                    >
                      <h2 className="text-lg font-semibold text-stone-900 mb-3">{faq.question}</h2>
                      <p className="text-stone-600">{faq.answer}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Container>
          </section>
        </div>
      </div>
      <MarketingChatWidget />
    </RadiantLayout>
  )
}

export default FaqPage
