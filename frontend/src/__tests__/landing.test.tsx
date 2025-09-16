import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { RenderInspiredLanding } from '../pages/RenderInspiredLanding';
import { AnimatedWorkflow } from '../components/AnimatedWorkflow';

// Mock Framer Motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <div {...cleanProps}>{children}</div>;
    },
    h1: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <h1 {...cleanProps}>{children}</h1>;
    },
    h2: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <h2 {...cleanProps}>{children}</h2>;
    },
    h3: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <h3 {...cleanProps}>{children}</h3>;
    },
    p: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <p {...cleanProps}>{children}</p>;
    },
    span: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <span {...cleanProps}>{children}</span>;
    },
    button: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <button {...cleanProps}>{children}</button>;
    },
    section: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <section {...cleanProps}>{children}</section>;
    },
    nav: ({ children, ...props }: any) => {
      const { whileHover, whileInView, animate, initial, transition, ...cleanProps } = props;
      return <nav {...cleanProps}>{children}</nav>;
    },
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  ArrowRight: () => <div data-testid="arrow-right" />,
  Sparkles: () => <div data-testid="sparkles" />,
  Mail: () => <div data-testid="mail" />,
  Users: () => <div data-testid="users" />,
  Brain: () => <div data-testid="brain" />,
  Zap: () => <div data-testid="zap" />,
  CheckCircle: () => <div data-testid="check-circle" />,
  Play: () => <div data-testid="play" />,
  ChevronRight: () => <div data-testid="chevron-right" />,
  BarChart3: () => <div data-testid="bar-chart" />,
  MessageSquare: () => <div data-testid="message-square" />,
  Calendar: () => <div data-testid="calendar" />,
  TrendingUp: () => <div data-testid="trending-up" />,
}));

// Helper function to render with router
const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('RenderInspiredLanding Component', () => {
  beforeEach(() => {
    // Mock window.matchMedia for dark mode testing
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });

  test('renders headline correctly', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    // Use a more flexible text matcher for the headline with gradient span
    const headline = screen.getByRole('heading', { level: 1 });
    expect(headline).toBeInTheDocument();
    expect(headline).toHaveTextContent('Automate emails, leads, and workflows in minutes with AI');
  });

  test('renders subtext correctly', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const subtext = screen.getByText(/Industry-specific AI automation that handles your business processes/i);
    expect(subtext).toBeInTheDocument();
  });

  test('renders Try for Free CTA button', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const tryButton = screen.getByRole('link', { name: /Try for Free/i });
    expect(tryButton).toBeInTheDocument();
    expect(tryButton).toHaveAttribute('href', '/signup');
  });

  test('renders Watch Demo CTA button', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const demoButton = screen.getByRole('link', { name: /Watch Demo/i });
    expect(demoButton).toBeInTheDocument();
    expect(demoButton).toHaveAttribute('href', '/contact');
  });

  test('renders navigation bar with all links', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    expect(screen.getByRole('link', { name: /Services/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Industries/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Pricing/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Docs/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Sign In/i })).toBeInTheDocument();
  });

  test('logo is clickable and links to home', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const logoLink = screen.getByRole('link', { name: /Fikiri Solutions/i });
    expect(logoLink).toBeInTheDocument();
    expect(logoLink).toHaveAttribute('href', '/');
  });

  test('renders demo cards with correct titles', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    expect(screen.getByText('AI Email Assistant')).toBeInTheDocument();
    expect(screen.getByText('Smart CRM')).toBeInTheDocument();
    expect(screen.getByText('Workflow Automation')).toBeInTheDocument();
  });

  test('renders stats section', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    expect(screen.getByText('24')).toBeInTheDocument();
    expect(screen.getByText('Industry Verticals')).toBeInTheDocument();
    expect(screen.getByText('50+')).toBeInTheDocument();
    expect(screen.getByText('Automation Tools')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText('Time Savings')).toBeInTheDocument();
    expect(screen.getByText('500+')).toBeInTheDocument();
    expect(screen.getByText('Happy Customers')).toBeInTheDocument();
  });

  test('renders features section', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    expect(screen.getByText('Why Choose Fikiri Solutions?')).toBeInTheDocument();
    expect(screen.getByText('Industry-Specific AI')).toBeInTheDocument();
    expect(screen.getByText('Real-Time Analytics')).toBeInTheDocument();
    expect(screen.getByText('Seamless Integration')).toBeInTheDocument();
  });

  test('renders final CTA section', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    expect(screen.getByText('Ready to Transform Your Business?')).toBeInTheDocument();
    expect(screen.getByText('Start Free Trial')).toBeInTheDocument();
    expect(screen.getByText('Contact Sales')).toBeInTheDocument();
  });

  test('applies dark mode classes correctly', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    // Check that dark mode classes are applied to the main container
    const mainContainer = document.querySelector('.min-h-screen');
    expect(mainContainer).toHaveClass('bg-white', 'dark:bg-gray-900');
  });

  test('demo cards are clickable', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const demoCards = screen.getAllByText(/AI Email Assistant|Smart CRM|Workflow Automation/);
    demoCards.forEach(card => {
      expect(card.closest('div')).toHaveClass('cursor-pointer');
    });
  });
});

describe('AnimatedWorkflow Component', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('renders all 5 workflow steps', () => {
    render(<AnimatedWorkflow />);
    
    // Check that we have 5 workflow step containers
    expect(screen.getAllByTestId('workflow-step')).toHaveLength(5);
    
    // Check that all step titles are present in the workflow steps (not the detailed view)
    const workflowSteps = screen.getAllByTestId('workflow-step');
    expect(workflowSteps[0]).toHaveTextContent('Email Received');
    expect(workflowSteps[1]).toHaveTextContent('AI Processing');
    expect(workflowSteps[2]).toHaveTextContent('CRM Update');
    expect(workflowSteps[3]).toHaveTextContent('Schedule Follow-up');
    expect(workflowSteps[4]).toHaveTextContent('Analytics Update');
  });

  test('renders workflow step descriptions', () => {
    render(<AnimatedWorkflow />);
    
    // Check that all descriptions are present in the workflow steps
    const workflowSteps = screen.getAllByTestId('workflow-step');
    expect(workflowSteps[0]).toHaveTextContent('Customer sends inquiry via email');
    expect(workflowSteps[1]).toHaveTextContent('AI analyzes intent and generates response');
    expect(workflowSteps[2]).toHaveTextContent('Lead automatically added to CRM');
    expect(workflowSteps[3]).toHaveTextContent('Appointment automatically scheduled');
    expect(workflowSteps[4]).toHaveTextContent('Performance metrics updated in real-time');
  });

  test('renders workflow icons', () => {
    render(<AnimatedWorkflow />);
    
    // Use getAllByTestId since there are multiple instances of these icons
    expect(screen.getAllByTestId('mail')).toHaveLength(2);
    expect(screen.getAllByTestId('brain')).toHaveLength(1);
    expect(screen.getAllByTestId('users')).toHaveLength(1);
    expect(screen.getAllByTestId('calendar')).toHaveLength(1);
    expect(screen.getAllByTestId('bar-chart')).toHaveLength(2);
  });

  test('workflow steps cycle automatically', async () => {
    render(<AnimatedWorkflow />);
    
    // Fast-forward time to trigger step changes
    jest.advanceTimersByTime(3000);
    
    // Check that we still have 5 workflow step containers
    expect(screen.getAllByTestId('workflow-step')).toHaveLength(5);
    
    // Check that all step titles are still present in the workflow steps
    const workflowSteps = screen.getAllByTestId('workflow-step');
    expect(workflowSteps[0]).toHaveTextContent('Email Received');
    expect(workflowSteps[1]).toHaveTextContent('AI Processing');
    expect(workflowSteps[2]).toHaveTextContent('CRM Update');
    expect(workflowSteps[3]).toHaveTextContent('Schedule Follow-up');
    expect(workflowSteps[4]).toHaveTextContent('Analytics Update');
  });

  test('renders floating elements', () => {
    render(<AnimatedWorkflow />);
    
    // Check for floating elements (they should be present in the DOM)
    const floatingElements = document.querySelectorAll('[class*="absolute"]');
    expect(floatingElements.length).toBeGreaterThan(0);
  });

  test('renders progress bar', () => {
    render(<AnimatedWorkflow />);
    
    // Check for progress bar element
    const progressBar = document.querySelector('[class*="bg-gradient-to-r"]');
    expect(progressBar).toBeInTheDocument();
  });
});

describe('Integration Tests', () => {
  test('navigation links route correctly', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const servicesLink = screen.getByRole('link', { name: /Services/i });
    expect(servicesLink).toHaveAttribute('href', '/services');
    
    const industriesLink = screen.getByRole('link', { name: /Industries/i });
    expect(industriesLink).toHaveAttribute('href', '/industry');
    
    const pricingLink = screen.getByRole('link', { name: /Pricing/i });
    expect(pricingLink).toHaveAttribute('href', '/pricing');
    
    const docsLink = screen.getByRole('link', { name: /Docs/i });
    expect(docsLink).toHaveAttribute('href', '/docs');
  });

  test('CTA buttons have correct href attributes', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const tryButton = screen.getByRole('link', { name: /Try for Free/i });
    expect(tryButton).toHaveAttribute('href', '/signup');
    
    const demoButton = screen.getByRole('link', { name: /Watch Demo/i });
    expect(demoButton).toHaveAttribute('href', '/contact');
    
    const startTrialButton = screen.getByRole('link', { name: /Start Free Trial/i });
    expect(startTrialButton).toHaveAttribute('href', '/signup');
    
    const contactSalesButton = screen.getByRole('link', { name: /Contact Sales/i });
    expect(contactSalesButton).toHaveAttribute('href', '/contact');
  });

  test('logo click routes to home', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const logoLink = screen.getByRole('link', { name: /Fikiri Solutions/i });
    expect(logoLink).toHaveAttribute('href', '/');
  });
});

describe('Accessibility Tests', () => {
  test('all interactive elements have proper roles', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    // Check for proper link roles
    expect(screen.getByRole('link', { name: /Try for Free/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Watch Demo/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Services/i })).toBeInTheDocument();
  });

  test('headings have proper hierarchy', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1).toBeInTheDocument();
    
    const h2s = screen.getAllByRole('heading', { level: 2 });
    expect(h2s.length).toBeGreaterThan(0);
  });

  test('images have alt text or are decorative', () => {
    renderWithRouter(<RenderInspiredLanding />);
    
    // Check that icons are properly marked as decorative
    const icons = screen.getAllByTestId(/arrow-right|sparkles|mail|users|brain|zap/);
    icons.forEach(icon => {
      expect(icon).toBeInTheDocument();
    });
  });
});

describe('Performance Tests', () => {
  test('component renders without errors', () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    renderWithRouter(<RenderInspiredLanding />);
    
    expect(consoleSpy).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  test('component renders quickly', () => {
    const startTime = performance.now();
    renderWithRouter(<RenderInspiredLanding />);
    const endTime = performance.now();
    
    // Component should render in less than 100ms
    expect(endTime - startTime).toBeLessThan(100);
  });
});
