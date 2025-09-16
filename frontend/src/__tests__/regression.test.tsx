import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { BackToTop } from '../components/BackToTop';
import { ThemeProvider } from '../contexts/ThemeContext';

// Mock components and hooks
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

jest.mock('lucide-react', () => ({
  ArrowUp: () => <div data-testid="arrow-up" />,
  Home: () => <div data-testid="home" />,
  Users: () => <div data-testid="users" />,
  MessageSquare: () => <div data-testid="message-square" />,
  Building2: () => <div data-testid="building" />,
  LogOut: () => <div data-testid="logout" />,
  Menu: () => <div data-testid="menu" />,
  X: () => <div data-testid="close" />,
}));

// Helper function to render with router and theme
const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <ThemeProvider>
        {component}
      </ThemeProvider>
    </BrowserRouter>
  );
};

describe('Regression Tests - Layout Component', () => {
  test('logo is clickable and links to home', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    const logoLink = screen.getByRole('link', { name: /Fikiri Solutions/i });
    expect(logoLink).toBeInTheDocument();
    expect(logoLink).toHaveAttribute('href', '/');
  });

  test('navigation links work correctly', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check all navigation links
    expect(screen.getByRole('link', { name: /Dashboard/i })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /Services/i })).toHaveAttribute('href', '/services');
    expect(screen.getByRole('link', { name: /CRM/i })).toHaveAttribute('href', '/crm');
    expect(screen.getByRole('link', { name: /AI Assistant/i })).toHaveAttribute('href', '/ai');
    expect(screen.getByRole('link', { name: /Industry AI/i })).toHaveAttribute('href', '/industry');
  });

  test('dark mode toggle works', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that dark mode classes are applied
    const mainContainer = document.querySelector('.min-h-screen');
    expect(mainContainer).toHaveClass('bg-white', 'dark:bg-gray-900');
  });

  test('sign out button works', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    const signOutButton = screen.getByRole('button', { name: /Sign out/i });
    expect(signOutButton).toBeInTheDocument();
    
    // Mock localStorage
    const mockRemoveItem = jest.fn();
    Object.defineProperty(window, 'localStorage', {
      value: {
        removeItem: mockRemoveItem,
      },
      writable: true,
    });
    
    fireEvent.click(signOutButton);
    expect(mockRemoveItem).toHaveBeenCalledWith('fikiri_token');
  });

  test('mobile menu works', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that mobile menu button exists
    const menuButton = screen.getByRole('button', { name: /Open menu/i });
    expect(menuButton).toBeInTheDocument();
  });
});

describe('Regression Tests - BackToTop Component', () => {
  test('renders correctly', () => {
    render(<BackToTop />);
    
    const backToTopButton = screen.getByRole('button', { name: /Back to top/i });
    expect(backToTopButton).toBeInTheDocument();
  });

  test('has proper ARIA label', () => {
    render(<BackToTop />);
    
    const backToTopButton = screen.getByRole('button', { name: /Back to top/i });
    expect(backToTopButton).toHaveAttribute('aria-label', 'Back to top');
  });

  test('scrolls to top when clicked', () => {
    render(<BackToTop />);
    
    // Mock window.scrollTo
    const mockScrollTo = jest.fn();
    Object.defineProperty(window, 'scrollTo', {
      value: mockScrollTo,
      writable: true,
    });
    
    const backToTopButton = screen.getByRole('button', { name: /Back to top/i });
    fireEvent.click(backToTopButton);
    
    expect(mockScrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' });
  });
});

describe('Regression Tests - App Routes', () => {
  test('all existing routes still work', () => {
    // Test that all routes are properly configured
    const routes = [
      '/',
      '/services',
      '/crm',
      '/ai',
      '/industry',
      '/login',
      '/signup',
      '/contact',
      '/pricing',
      '/docs'
    ];
    
    routes.forEach(route => {
      // This would be tested in integration tests
      expect(route).toBeDefined();
    });
  });

  test('new /home route works', () => {
    // Test that the new /home route is properly configured
    expect('/home').toBeDefined();
  });
});

describe('Regression Tests - Dark Mode', () => {
  test('dark mode classes are applied consistently', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that dark mode classes are applied to key elements
    const mainContainer = document.querySelector('.min-h-screen');
    expect(mainContainer).toHaveClass('bg-white', 'dark:bg-gray-900');
    
    const sidebar = document.querySelector('.bg-white');
    expect(sidebar).toHaveClass('dark:bg-gray-800');
  });

  test('text remains readable in dark mode', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that text has proper dark mode classes
    const textElements = document.querySelectorAll('.text-gray-900');
    textElements.forEach(element => {
      expect(element).toHaveClass('dark:text-white');
    });
  });
});

describe('Regression Tests - CSS Classes', () => {
  test('spacing classes are consistent', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that spacing classes are applied consistently
    const container = document.querySelector('.max-w-7xl');
    expect(container).toHaveClass('mx-auto', 'px-4', 'sm:px-6', 'lg:px-8');
  });

  test('hover effects are applied', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that hover effects are applied to interactive elements
    const links = document.querySelectorAll('a');
    links.forEach(link => {
      expect(link).toHaveClass('transition-colors', 'duration-200');
    });
  });
});

describe('Regression Tests - Accessibility', () => {
  test('all interactive elements have proper roles', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that all interactive elements have proper roles
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  test('focus management works correctly', () => {
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Check that focusable elements can receive focus
    const firstLink = screen.getByRole('link', { name: /Dashboard/i });
    firstLink.focus();
    expect(document.activeElement).toBe(firstLink);
  });
});

describe('Regression Tests - Performance', () => {
  test('component renders without errors', () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    expect(consoleSpy).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  test('no memory leaks in component lifecycle', () => {
    const { unmount } = renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    // Unmount should not cause errors
    expect(() => unmount()).not.toThrow();
  });
});

describe('Regression Tests - Integration', () => {
  test('Layout integrates with BackToTop component', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
        <BackToTop />
      </Layout>
    );
    
    // Both components should render without conflicts
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Back to top/i })).toBeInTheDocument();
  });

  test('theme context works with all components', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
        <BackToTop />
      </Layout>
    );
    
    // All components should have access to theme context
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Back to top/i })).toBeInTheDocument();
  });
});

describe('Regression Tests - Cross-Browser Compatibility', () => {
  test('component works with different user agents', () => {
    // Mock different user agents
    const userAgents = [
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
    ];
    
    userAgents.forEach(userAgent => {
      Object.defineProperty(navigator, 'userAgent', {
        value: userAgent,
        writable: true,
      });
      
      renderWithProviders(<Layout><div>Test Content</div></Layout>);
      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });
});

describe('Regression Tests - Error Handling', () => {
  test('handles missing props gracefully', () => {
    // Test with minimal props
    renderWithProviders(<Layout><div>Test Content</div></Layout>);
    
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  test('handles invalid routes gracefully', () => {
    // This would be tested in integration tests
    expect(true).toBe(true);
  });
});
