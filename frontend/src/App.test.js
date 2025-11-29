import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import App from './App';

// Mock localStorage
const localStorageMock = {
  store: {},
  getItem: jest.fn((key) => localStorageMock.store[key] || null),
  setItem: jest.fn((key, value) => { localStorageMock.store[key] = value; }),
  removeItem: jest.fn((key) => { delete localStorageMock.store[key]; }),
  clear: jest.fn(() => { localStorageMock.store = {}; }),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock the API module to avoid network requests in tests
jest.mock('./api', () => {
  const mockApi = {
    get: jest.fn().mockResolvedValue({
      data: {
        status: 'operational',
        scenarios: { total: 0, active: 0 },
        labs: { total: 0, active: 0, total_containers: 0, total_networks: 0 },
        safety: { air_gap_enforced: true, external_network_blocked: true, real_rf_blocked: true }
      }
    }),
  };
  return {
    default: mockApi,
    scenarioApi: {
      list: jest.fn().mockResolvedValue({ data: [] }),
      get: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
      listActive: jest.fn().mockResolvedValue({ data: [] }),
    },
    topologyApi: {
      list: jest.fn().mockResolvedValue({ data: [] }),
      get: jest.fn(),
    },
    labApi: {
      list: jest.fn().mockResolvedValue({ data: [] }),
      listActive: jest.fn().mockResolvedValue({ data: [] }),
      get: jest.fn(),
      stop: jest.fn(),
    },
    recordingApi: {
      list: jest.fn().mockResolvedValue({ data: { recordings: [] } }),
      get: jest.fn(),
      getPlayback: jest.fn().mockResolvedValue({ data: { session: {}, events: [] } }),
    },
    authApi: {
      getUser: jest.fn(),
      getToken: jest.fn(),
      login: jest.fn(),
      logout: jest.fn(),
      setToken: jest.fn(),
      setUser: jest.fn(),
    },
  };
});

// Import the mocked module
import { authApi } from './api';

describe('App - Login screen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    authApi.getUser.mockReturnValue(null);
    authApi.getToken.mockReturnValue(null);
  });

  test('renders login screen when not authenticated', async () => {
    render(<App />);
    expect(screen.getByText(/Sign in to continue/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter password/i)).toBeInTheDocument();
  });

  test('renders demo accounts info on login screen', async () => {
    render(<App />);
    expect(screen.getByText(/Demo accounts/i)).toBeInTheDocument();
    expect(screen.getByText(/admin \/ admin123/i)).toBeInTheDocument();
  });
});

describe('App - Authenticated', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    authApi.getUser.mockReturnValue({
      username: 'testuser',
      role: 'admin',
      full_name: 'Test User'
    });
    authApi.getToken.mockReturnValue('test-token');
  });

  test('renders main app when authenticated', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Test User/i)).toBeInTheDocument();
    });
  });

  test('renders dashboard for admin users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    });
  });

  test('renders scenarios tab when logged in', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/📝 Scenarios/i)).toBeInTheDocument();
    });
  });

  test('renders create scenario button when on scenarios view', async () => {
    render(<App />);
    // Click on Scenarios tab
    await waitFor(() => {
      fireEvent.click(screen.getByText(/📝 Scenarios/i));
    });
    await waitFor(() => {
      expect(screen.getByText(/Create New Scenario/i)).toBeInTheDocument();
    });
  });

  test('renders logout button when logged in', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Logout/i)).toBeInTheDocument();
    });
  });

  test('renders safety warning in footer', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Training use only/i)).toBeInTheDocument();
    });
  });

  test('renders recordings tab for admin users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/📼 Recordings/i)).toBeInTheDocument();
    });
  });

  test('can navigate to recordings view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/📼 Recordings/i));
    });
    // Verify the recordings tab is active (has the blue active style)
    await waitFor(() => {
      const recordingsButton = screen.getByText(/📼 Recordings/i);
      expect(recordingsButton).toHaveStyle({ backgroundColor: 'rgb(0, 123, 255)' });
    });
  });
});
