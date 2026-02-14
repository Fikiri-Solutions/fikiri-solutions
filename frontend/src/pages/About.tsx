import React from 'react'
import { RadiantLayout, Container, Gradient, AnimatedBackground } from '../components/radiant'

export const About: React.FC = () => {
  return (
    <RadiantLayout>
      <div className="min-h-screen bg-background text-foreground relative">
        <div className="absolute inset-0 fikiri-gradient-animated">
          <AnimatedBackground />
        </div>
        {/* Hero */}
        <section className="relative py-16 sm:py-20 z-10">
          <Gradient className="absolute inset-x-2 top-0 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-20" />
          <Container className="relative">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-4xl font-bold text-foreground mb-4 sm:text-5xl">
                About Fikiri Solutions
              </h1>
              <p className="text-xl text-muted-foreground">
                We help small and large businesses save money through automation.
              </p>
            </div>
          </Container>
        </section>

        {/* Business Information */}
        <section className="py-16 relative z-10">
          <Container>
            <div className="bg-card/90 backdrop-blur-sm rounded-2xl border border-border shadow-sm p-8 mb-12">
              <h2 className="text-2xl font-semibold text-foreground mb-6">
                Business Information
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-lg font-medium text-foreground mb-4">
                    Company Details
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <span className="font-medium text-muted-foreground">Business Name:</span>
                      <p className="text-foreground">Fikiri Solutions</p>
                    </div>
                    <div>
                      <span className="font-medium text-muted-foreground">Industry:</span>
                      <p className="text-foreground">AI-Powered Business Automation</p>
                    </div>
                    <div>
                      <span className="font-medium text-muted-foreground">Website:</span>
                      <p className="text-foreground">https://fikirisolutions.com</p>
                    </div>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-foreground mb-4">
                    Contact Information
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <span className="font-medium text-muted-foreground">Location:</span>
                      <p className="text-foreground">
                        Florida, United States
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Services */}
            <h2 className="text-2xl font-semibold text-foreground mb-6">
              Our Services
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
              <div className="text-center bg-card/90 backdrop-blur-sm rounded-2xl border border-border shadow-sm p-8">
                <div className="bg-brand-primary/15 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">📧</span>
                </div>
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Email Automation
                </h3>
                <p className="text-muted-foreground text-sm">
                  AI-powered email processing and response automation
                </p>
              </div>
              <div className="text-center bg-card/90 backdrop-blur-sm rounded-2xl border border-border shadow-sm p-8">
                <div className="bg-brand-primary/15 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">👥</span>
                </div>
                <h3 className="text-lg font-medium text-foreground mb-2">
                  CRM Management
                </h3>
                <p className="text-muted-foreground text-sm">
                  Customer relationship management and lead tracking
                </p>
              </div>
              <div className="text-center bg-card/90 backdrop-blur-sm rounded-2xl border border-border shadow-sm p-8">
                <div className="bg-brand-primary/15 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🤖</span>
                </div>
                <h3 className="text-lg font-medium text-foreground mb-2">
                  AI Assistant
                </h3>
                <p className="text-muted-foreground text-sm">
                  Intelligent business automation and analytics
                </p>
              </div>
            </div>

            {/* Specializations */}
            <h2 className="text-2xl font-semibold text-foreground mb-6">
              Industry Specializations
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 bg-card/90 backdrop-blur-sm border border-border rounded-2xl shadow-sm">
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Landscaping
                </h3>
                <p className="text-muted-foreground text-sm">
                  Automated client communication and project management
                </p>
              </div>
              <div className="text-center p-6 bg-card/90 backdrop-blur-sm border border-border rounded-2xl shadow-sm">
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Restaurants
                </h3>
                <p className="text-muted-foreground text-sm">
                  Order management and customer service automation
                </p>
              </div>
              <div className="text-center p-6 bg-card/90 backdrop-blur-sm border border-border rounded-2xl shadow-sm">
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Medical Practices
                </h3>
                <p className="text-muted-foreground text-sm">
                  Patient communication and appointment scheduling
                </p>
              </div>
            </div>
          </Container>
        </section>
      </div>
    </RadiantLayout>
  )
}
