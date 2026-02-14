import { Container } from './Container'
import { Heading, Subheading } from './Text'

const testimonials = [
  {
    name: 'Sarah M.',
    title: 'Operations Lead',
    quote:
      'Fikiri cut our response time to leads in half. The AI drafts feel human and we just tweak and send.',
  },
  {
    name: 'James K.',
    title: 'Small Business Owner',
    quote:
      'Finally one place for email, CRM, and scheduling. We dropped three tools and our team actually uses this.',
  },
  {
    name: 'Priya L.',
    title: 'Sales Director',
    quote:
      'The calendar integration and reminders mean we show up prepared. Our no-show rate dropped noticeably.',
  },
]

export function Testimonials() {
  return (
    <section className="py-24 sm:py-32">
      <Container>
        <Subheading>Testimonials</Subheading>
        <Heading as="h2" className="mt-2 max-w-3xl">
          Trusted by teams who care about response time and clarity.
        </Heading>
        <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {testimonials.map(({ name, title, quote }) => (
            <blockquote
              key={name}
              className="rounded-2xl bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm p-8 ring-1 ring-black/10 dark:ring-white/15"
            >
              <p className="text-foreground text-lg font-medium">{quote}</p>
              <footer className="mt-6">
                <cite className="not-italic">
                  <span className="block font-semibold text-foreground">{name}</span>
                  <span className="block text-sm text-muted-foreground">{title}</span>
                </cite>
              </footer>
            </blockquote>
          ))}
        </div>
      </Container>
    </section>
  )
}
