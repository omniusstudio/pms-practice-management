import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { vi } from 'vitest';

// Mock AuthContext for testing
const mockAuthContext = {
  user: {
    id: 'test-user-id',
    name: 'Test User',
    email: 'test@example.com',
    roles: ['clinician'],
  },
  isAuthenticated: true,
  isLoading: false,
  error: null,
  login: vi.fn(),
  logout: vi.fn(),
  clearError: vi.fn(),
};

// Create a proper mock context
const MockAuthContext = React.createContext(mockAuthContext);

// Mock AuthProvider that provides the mock context
const MockAuthProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <MockAuthContext.Provider value={mockAuthContext}>
      <div data-testid="mock-auth-provider">
        {children}
      </div>
    </MockAuthContext.Provider>
  );
};

// Mock useAuth hook
const mockUseAuth = () => React.useContext(MockAuthContext);

// Mock the entire AuthContext module
vi.mock('../src/contexts/AuthContext', () => ({
  AuthProvider: MockAuthProvider,
  useAuth: mockUseAuth,
}));

// Mock Logger to prevent console noise in tests
vi.mock('../src/utils/logger', () => ({
  Logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
    auditAction: vi.fn(),
  },
}));

// Mock http-client
vi.mock('../src/utils/http-client', () => ({
  useHttpClient: () => ({
    api: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      patch: vi.fn(),
    },
  }),
}));

// Mock authService
vi.mock('../src/services/authService', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn().mockResolvedValue(mockAuthContext.user),
    isAuthenticated: vi.fn().mockReturnValue(true),
    getToken: vi.fn().mockReturnValue('mock-token'),
    setToken: vi.fn(),
  },
}));

// Mock React Router
vi.mock('react-router-dom', () => ({
  RouterProvider: ({ router: _router }: any) => {
    return React.createElement('div', { 'data-testid': 'mock-router' }, [
      React.createElement('div', { key: 'greeting' }, 'Good morning, John Doe!'),
      React.createElement('div', { key: 'welcome' }, 'Welcome to the Patient Management System'),
      React.createElement('div', { key: 'actions' }, 'Quick Actions'),
    ]);
  },
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/dashboard', search: '', hash: '', state: null }),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
  Link: ({ children, to, ...props }: any) => React.createElement('a', { href: to, ...props }, children),
  Navigate: ({ to }: any) => React.createElement('div', { 'data-testid': 'navigate-to' }, to),
  BrowserRouter: ({ children }: any) => React.createElement('div', { 'data-testid': 'browser-router' }, children),
  createBrowserRouter: () => ({}),
}));

// Mock the router configuration
vi.mock('../src/router', () => ({
  router: {
    routes: [],
  },
  routes: {
    home: '/',
    login: '/login',
    dashboard: '/dashboard',
    patients: '/patients',
    appointments: '/appointments',
    billing: '/billing',
    reports: '/reports',
    settings: '/settings',
    unauthorized: '/unauthorized',
  },
}));

// Custom render function that includes providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  return (
    <MockAuthProvider>
      {children}
    </MockAuthProvider>
  );
};

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, { wrapper: AllTheProviders, ...options });

export * from '@testing-library/react';
export { customRender as render };
export { mockAuthContext };
