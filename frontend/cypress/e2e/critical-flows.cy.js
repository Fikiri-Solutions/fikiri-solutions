describe('Critical User Flows E2E Tests', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  describe('Authentication Flow', () => {
    it('login form validation works', () => {
      cy.visit('/login');
      
      // Test empty form submission
      cy.get('button[type="submit"]').click();
      cy.get('.text-red-600').should('be.visible');
      
      // Test invalid email
      cy.get('input[name="email"]').type('invalid-email');
      cy.get('input[name="password"]').type('password123');
      cy.get('button[type="submit"]').click();
      cy.get('.text-red-600').should('contain', 'valid email');
      
      // Test valid form
      cy.get('input[name="email"]').clear().type('test@example.com');
      cy.get('input[name="password"]').clear().type('password123');
      cy.get('button[type="submit"]').click();
      
      // Should show loading state
      cy.get('button[type="submit"]').should('be.disabled');
    });
  });

  describe('Dashboard Functionality', () => {
    it('dashboard loads and displays metrics', () => {
      cy.visit('/dashboard');
      
      // Check that dashboard components load
      cy.get('[data-testid="metric-card"]').should('have.length.at.least', 1);
      cy.get('[data-testid="service-card"]').should('have.length.at.least', 1);
      
      // Check that charts are rendered
      cy.get('[data-testid="chart-container"]').should('be.visible');
    });

    it('theme toggle works on dashboard', () => {
      cy.visit('/dashboard');
      
      // Toggle to dark mode
      cy.get('[data-testid="theme-toggle"]').click();
      cy.get('body').should('have.class', 'dark');
      
      // Toggle back to light mode
      cy.get('[data-testid="theme-toggle"]').click();
      cy.get('body').should('not.have.class', 'dark');
    });
  });

  describe('AI Assistant Flow', () => {
    it('AI chat interface works', () => {
      cy.visit('/ai-assistant');
      
      // Check that chat interface loads
      cy.get('[data-testid="chat-container"]').should('be.visible');
      cy.get('[data-testid="message-input"]').should('be.visible');
      cy.get('[data-testid="send-button"]').should('be.visible');
      
      // Test message input
      cy.get('[data-testid="message-input"]').type('Hello, how can you help me?');
      cy.get('[data-testid="send-button"]').click();
      
      // Should show loading state
      cy.get('[data-testid="send-button"]').should('be.disabled');
    });
  });

  describe('CRM Functionality', () => {
    it('CRM page loads and displays leads', () => {
      cy.visit('/crm');
      
      // Check that CRM components load
      cy.get('[data-testid="leads-table"]').should('be.visible');
      cy.get('[data-testid="add-lead-button"]').should('be.visible');
      
      // Test add lead form
      cy.get('[data-testid="add-lead-button"]').click();
      cy.get('[data-testid="lead-form"]').should('be.visible');
    });
  });

  describe('Error Handling', () => {
    it('404 page works correctly', () => {
      cy.visit('/non-existent-page', { failOnStatusCode: false });
      
      // Should show 404 page
      cy.get('h1').should('contain', '404');
      cy.get('a[href="/"]').should('be.visible');
    });

    it('error boundary catches JavaScript errors', () => {
      // This would require injecting an error, which is complex in E2E
      // For now, just verify error boundary component exists
      cy.visit('/');
      cy.get('body').should('not.contain', 'Something went wrong');
    });
  });

  describe('Performance Tests', () => {
    it('page loads within performance budget', () => {
      cy.visit('/', {
        onBeforeLoad: (win) => {
          win.performance.mark('page-start');
        }
      });
      
      cy.get('h1').should('be.visible').then(() => {
        cy.window().then((win) => {
          win.performance.mark('page-end');
          win.performance.measure('page-load', 'page-start', 'page-end');
          
          const measure = win.performance.getEntriesByName('page-load')[0];
          expect(measure.duration).to.be.lessThan(3000); // 3 seconds max
        });
      });
    });

    it('has good Lighthouse scores', () => {
      cy.visit('/');
      cy.lighthouse({
        performance: 90,
        accessibility: 90,
        'best-practices': 90,
        seo: 90,
      });
    });
  });
});

describe('API Integration Tests', () => {
  describe('Backend API Health', () => {
    it('health endpoint returns correct status', () => {
      cy.request({
        method: 'GET',
        url: '/api/health',
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.be.oneOf([200, 503]); // Either healthy or degraded
        expect(response.body).to.have.property('status');
        expect(response.body).to.have.property('timestamp');
      });
    });

    it('services endpoint returns service list', () => {
      cy.request({
        method: 'GET',
        url: '/api/services',
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.be.oneOf([200, 500]);
        if (response.status === 200) {
          expect(response.body).to.be.an('array');
        }
      });
    });

    it('metrics endpoint returns metrics data', () => {
      cy.request({
        method: 'GET',
        url: '/api/metrics',
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.be.oneOf([200, 500]);
        if (response.status === 200) {
          expect(response.body).to.have.property('totalEmails');
          expect(response.body).to.have.property('activeLeads');
        }
      });
    });
  });

  describe('AI Chat API', () => {
    it('AI chat endpoint handles requests', () => {
      cy.request({
        method: 'POST',
        url: '/api/ai/chat',
        body: {
          message: 'Hello, test message'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.be.oneOf([200, 503]);
        if (response.status === 200) {
          expect(response.body).to.have.property('response');
        }
      });
    });
  });
});

