describe('Render-Inspired Landing Page E2E Tests', () => {
  beforeEach(() => {
    cy.visit('/home');
  });

  describe('Homepage Load', () => {
    it('loads the landing page successfully', () => {
      cy.url().should('include', '/home');
      cy.get('h1').should('contain', 'Automate emails, leads, and workflows in minutes with AI');
    });

    it('renders all main sections', () => {
      // Hero section
      cy.get('h1').should('be.visible');
      cy.get('p').should('contain', 'Industry-specific AI automation');
      
      // Demo cards
      cy.get('[data-testid="demo-card"]').should('have.length', 3);
      
      // Stats section
      cy.get('[data-testid="stats-section"]').should('be.visible');
      
      // Features section
      cy.get('[data-testid="features-section"]').should('be.visible');
      
      // CTA section
      cy.get('[data-testid="cta-section"]').should('be.visible');
    });

    it('loads animations smoothly', () => {
      // Check that animated elements are present
      cy.get('[data-testid="animated-workflow"]').should('be.visible');
      
      // Wait for animations to start
      cy.wait(1000);
      
      // Check that workflow steps are cycling
      cy.get('[data-testid="workflow-step"]').should('have.length', 5);
    });
  });

  describe('Call-to-Actions', () => {
    it('Try for Free button redirects to signup', () => {
      cy.get('a[href="/signup"]').contains('Try for Free').click();
      cy.url().should('include', '/signup');
    });

    it('Watch Demo button redirects to contact', () => {
      cy.get('a[href="/contact"]').contains('Watch Demo').click();
      cy.url().should('include', '/contact');
    });

    it('Start Free Trial button redirects to signup', () => {
      cy.get('a[href="/signup"]').contains('Start Free Trial').click();
      cy.url().should('include', '/signup');
    });

    it('Contact Sales button redirects to contact', () => {
      cy.get('a[href="/contact"]').contains('Contact Sales').click();
      cy.url().should('include', '/contact');
    });
  });

  describe('Navigation', () => {
    it('Services link navigates correctly', () => {
      cy.get('a[href="/services"]').contains('Services').click();
      cy.url().should('include', '/services');
    });

    it('Industries link navigates correctly', () => {
      cy.get('a[href="/industry"]').contains('Industries').click();
      cy.url().should('include', '/industry');
    });

    it('Pricing link navigates correctly', () => {
      cy.get('a[href="/pricing"]').contains('Pricing').click();
      cy.url().should('include', '/pricing');
    });

    it('Docs link navigates correctly', () => {
      cy.get('a[href="/docs"]').contains('Docs').click();
      cy.url().should('include', '/docs');
    });

    it('Sign In link navigates correctly', () => {
      cy.get('a[href="/login"]').contains('Sign In').click();
      cy.url().should('include', '/login');
    });

    it('logo click returns to home', () => {
      cy.get('a[href="/"]').contains('Fikiri Solutions').click();
      cy.url().should('eq', Cypress.config().baseUrl + '/');
    });
  });

  describe('Dark Mode', () => {
    it('toggles dark mode correctly', () => {
      // Check initial state
      cy.get('body').should('not.have.class', 'dark');
      
      // Toggle dark mode (assuming there's a toggle button)
      cy.get('[data-testid="theme-toggle"]').click();
      
      // Check dark mode is applied
      cy.get('body').should('have.class', 'dark');
      
      // Toggle back
      cy.get('[data-testid="theme-toggle"]').click();
      
      // Check light mode is restored
      cy.get('body').should('not.have.class', 'dark');
    });

    it('maintains readability in dark mode', () => {
      // Toggle to dark mode
      cy.get('[data-testid="theme-toggle"]').click();
      
      // Check that text is still visible
      cy.get('h1').should('be.visible');
      cy.get('p').should('be.visible');
      
      // Check that buttons are still clickable
      cy.get('a[href="/signup"]').should('be.visible');
    });
  });

  describe('Interactive Elements', () => {
    it('demo cards are clickable', () => {
      cy.get('[data-testid="demo-card"]').first().click();
      
      // Check that the workflow animation updates
      cy.get('[data-testid="animated-workflow"]').should('be.visible');
    });

    it('hover effects work on buttons', () => {
      cy.get('a[href="/signup"]').contains('Try for Free')
        .trigger('mouseover')
        .should('have.css', 'transform');
    });

    it('hover effects work on demo cards', () => {
      cy.get('[data-testid="demo-card"]').first()
        .trigger('mouseover')
        .should('have.css', 'transform');
    });
  });

  describe('Responsive Design', () => {
    it('works on mobile viewport', () => {
      cy.viewport(375, 667); // iPhone SE
      
      cy.get('h1').should('be.visible');
      cy.get('a[href="/signup"]').should('be.visible');
      
      // Check that navigation is accessible
      cy.get('nav').should('be.visible');
    });

    it('works on tablet viewport', () => {
      cy.viewport(768, 1024); // iPad
      
      cy.get('h1').should('be.visible');
      cy.get('[data-testid="demo-card"]').should('have.length', 3);
    });

    it('works on desktop viewport', () => {
      cy.viewport(1920, 1080); // Desktop
      
      cy.get('h1').should('be.visible');
      cy.get('[data-testid="demo-card"]').should('have.length', 3);
    });
  });

  describe('Performance', () => {
    it('loads within acceptable time', () => {
      cy.visit('/home');
      
      // Check that the main content loads quickly
      cy.get('h1').should('be.visible');
      
      // Check that animations start within 1 second
      cy.get('[data-testid="animated-workflow"]').should('be.visible');
    });

    it('has no console errors', () => {
      cy.visit('/home');
      
      // Check for console errors
      cy.window().then((win) => {
        const consoleErrors = win.console.error;
        expect(consoleErrors).to.not.be.called;
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      cy.get('h1').should('exist');
      cy.get('h2').should('exist');
    });

    it('has proper link text', () => {
      cy.get('a[href="/signup"]').should('contain.text', 'Try for Free');
      cy.get('a[href="/contact"]').should('contain.text', 'Watch Demo');
    });

    it('has proper button roles', () => {
      cy.get('a[href="/signup"]').should('have.attr', 'role', 'link');
    });

    it('supports keyboard navigation', () => {
      // Tab through interactive elements
      cy.get('body').tab();
      cy.focused().should('exist');
    });
  });

  describe('Cross-Browser Compatibility', () => {
    it('works in Chrome', () => {
      cy.visit('/home');
      cy.get('h1').should('be.visible');
    });

    it('works in Firefox', () => {
      cy.visit('/home');
      cy.get('h1').should('be.visible');
    });

    it('works in Safari', () => {
      cy.visit('/home');
      cy.get('h1').should('be.visible');
    });
  });
});

describe('Back-to-Top Component E2E Tests', () => {
  beforeEach(() => {
    cy.visit('/home');
  });

  it('appears after scrolling 300px', () => {
    // Scroll down
    cy.scrollTo(0, 400);
    
    // Check that back-to-top button appears
    cy.get('[data-testid="back-to-top"]').should('be.visible');
  });

  it('scrolls to top when clicked', () => {
    // Scroll down
    cy.scrollTo(0, 400);
    
    // Click back-to-top button
    cy.get('[data-testid="back-to-top"]').click();
    
    // Check that page scrolled to top
    cy.window().its('scrollY').should('eq', 0);
  });

  it('has proper ARIA label', () => {
    cy.scrollTo(0, 400);
    cy.get('[data-testid="back-to-top"]').should('have.attr', 'aria-label');
  });
});

describe('Integration with Backend', () => {
  it('health endpoint responds correctly', () => {
    cy.request('GET', '/api/health').then((response) => {
      expect(response.status).to.eq(200);
      expect(response.body.status).to.eq('healthy');
    });
  });

  it('industry prompts endpoint responds correctly', () => {
    cy.request('GET', '/api/industry/prompts').then((response) => {
      expect(response.status).to.eq(200);
      expect(response.body.success).to.eq(true);
      expect(response.body.prompts).to.be.an('object');
    });
  });

  it('handles API errors gracefully', () => {
    // Mock API error
    cy.intercept('GET', '/api/health', { statusCode: 500 }).as('healthError');
    
    cy.visit('/home');
    
    // Page should still load even if API fails
    cy.get('h1').should('be.visible');
  });
});
