import { describe, it, expect } from 'vitest';
import { render, screen, waitFor, act } from './test-utils';
import App from '../src/App';

// Mock window.location for router tests
Object.defineProperty(window, 'location', {
  value: {
    pathname: '/',
    search: '',
    hash: '',
    state: null,
  },
  writable: true,
});

describe('App Component', () => {
  it('renders without crashing', async () => {
    await act(async () => {
      render(<App />);
    });

    // App should render the router and auth provider
    expect(screen.getAllByTestId('mock-auth-provider')).toHaveLength(2);
    expect(screen.getByTestId('mock-router')).toBeInTheDocument();
  });

  it('renders the dashboard when authenticated', async () => {
    await act(async () => {
      render(<App />);
    });

    // Wait for the dashboard to load
    await waitFor(() => {
      expect(screen.getByText(/Good (morning|afternoon|evening)/)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('displays user greeting on dashboard', async () => {
    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText('Good morning, John Doe!')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('shows dashboard welcome message', async () => {
    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText('Welcome to the Patient Management System')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('displays quick actions section', async () => {
    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});
