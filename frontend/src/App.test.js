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
      listTopologies: jest.fn().mockResolvedValue({ data: [] }),
      getNodeTypes: jest.fn().mockResolvedValue({ data: [] }),
      getConnectionTypes: jest.fn().mockResolvedValue({ data: [] }),
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
    progressApi: {
      getMyProgress: jest.fn().mockResolvedValue({ data: { level: 1, experience: 0 } }),
      getMyReport: jest.fn().mockResolvedValue({ data: { exercises_completed: 0 } }),
      getLeaderboard: jest.fn().mockResolvedValue({ data: { entries: [] } }),
      getAllProfiles: jest.fn().mockResolvedValue({ data: { profiles: [] } }),
      getBadges: jest.fn().mockResolvedValue({ data: { badges: [] } }),
      getSkillCategories: jest.fn().mockResolvedValue({ data: { categories: [] } }),
    },
    scheduleApi: {
      getUpcoming: jest.fn().mockResolvedValue({ data: { schedules: [] } }),
      getMySchedules: jest.fn().mockResolvedValue({ data: { schedules: [] } }),
      getCalendar: jest.fn().mockResolvedValue({ data: { schedules_by_day: {} } }),
      listSchedules: jest.fn().mockResolvedValue({ data: { schedules: [] } }),
    },
    sessionApi: {
      listSessions: jest.fn().mockResolvedValue({ data: { sessions: [] } }),
      getMySessions: jest.fn().mockResolvedValue({ data: { sessions: [] } }),
      getSession: jest.fn().mockResolvedValue({ data: {} }),
    },
    marketplaceApi: {
      listTemplates: jest.fn().mockResolvedValue({ data: { templates: [] } }),
      getPopular: jest.fn().mockResolvedValue({ data: { templates: [] } }),
      getRecent: jest.fn().mockResolvedValue({ data: { templates: [] } }),
      getMyTemplates: jest.fn().mockResolvedValue({ data: { templates: [] } }),
      getCategories: jest.fn().mockResolvedValue({ data: { categories: [] } }),
    },
    rfSimulationApi: {
      listSimulations: jest.fn().mockResolvedValue({ data: [] }),
      getFrequencyBands: jest.fn().mockResolvedValue({ data: [] }),
      getPredefinedThreats: jest.fn().mockResolvedValue({ data: [] }),
      getStatistics: jest.fn().mockResolvedValue({ data: null }),
    },
    backupApi: {
      listBackups: jest.fn().mockResolvedValue({ data: [] }),
      listSchedules: jest.fn().mockResolvedValue({ data: [] }),
      listSnapshots: jest.fn().mockResolvedValue({ data: [] }),
      getStatistics: jest.fn().mockResolvedValue({ data: {} }),
    },
    rateLimitApi: {
      getStatus: jest.fn().mockResolvedValue({ data: { enabled: true } }),
      getStatistics: jest.fn().mockResolvedValue({ data: {} }),
      getViolations: jest.fn().mockResolvedValue({ data: [] }),
      getTopUsers: jest.fn().mockResolvedValue({ data: [] }),
      getTopEndpoints: jest.fn().mockResolvedValue({ data: [] }),
      getMyStatus: jest.fn().mockResolvedValue({ data: { tier: 'admin' } }),
    },
    integrationsApi: {
      listIntegrations: jest.fn().mockResolvedValue({ data: [] }),
      getStatistics: jest.fn().mockResolvedValue({ data: {} }),
      getTactics: jest.fn().mockResolvedValue({ data: [] }),
      listTechniques: jest.fn().mockResolvedValue({ data: [] }),
      listMappings: jest.fn().mockResolvedValue({ data: [] }),
      listForwardingRules: jest.fn().mockResolvedValue({ data: [] }),
      listEmulationConfigs: jest.fn().mockResolvedValue({ data: [] }),
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

  test('renders progress tab for all users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/📈 Progress/i)).toBeInTheDocument();
    });
  });

  test('can navigate to progress view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/📈 Progress/i));
    });
    // Verify the progress dashboard is displayed
    await waitFor(() => {
      expect(screen.getByText(/Progress Dashboard/i)).toBeInTheDocument();
    });
  });

  test('renders schedule tab for all users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/📅 Schedule/i)).toBeInTheDocument();
    });
  });

  test('can navigate to schedule view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/📅 Schedule/i));
    });
    // Verify the schedule manager is displayed
    await waitFor(() => {
      expect(screen.getByText(/Exercise Schedule/i)).toBeInTheDocument();
    });
  });

  test('renders sessions tab for all users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/👥 Sessions/i)).toBeInTheDocument();
    });
  });

  test('can navigate to sessions view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/👥 Sessions/i));
    });
    // Verify the multi-user sessions is displayed
    await waitFor(() => {
      expect(screen.getByText(/Multi-User Sessions/i)).toBeInTheDocument();
    });
  });

  test('renders marketplace tab for all users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/🛒 Marketplace/i)).toBeInTheDocument();
    });
  });

  test('can navigate to marketplace view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/🛒 Marketplace/i));
    });
    // Verify the marketplace is displayed
    await waitFor(() => {
      expect(screen.getByText(/Scenario Marketplace/i)).toBeInTheDocument();
    });
  });

  test('renders topology editor tab for admin users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/🗺️ Topology/i)).toBeInTheDocument();
    });
  });

  test('can click topology editor tab for navigation', async () => {
    render(<App />);
    const topologyButton = await screen.findByText(/🗺️ Topology/i);
    fireEvent.click(topologyButton);
    // Verify the button is active after clicking
    await waitFor(() => {
      expect(topologyButton).toHaveStyle({ backgroundColor: 'rgb(0, 123, 255)' });
    });
  });

  test('renders RF/EW simulation tab for admin users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/📡 RF\/EW/i)).toBeInTheDocument();
    });
  });

  test('can click RF simulation tab for navigation', async () => {
    render(<App />);
    const rfButton = await screen.findByText(/📡 RF\/EW/i);
    fireEvent.click(rfButton);
    // Verify the button is active after clicking
    await waitFor(() => {
      expect(rfButton).toHaveStyle({ backgroundColor: 'rgb(0, 123, 255)' });
    });
  });

  test('renders backups tab for admin users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/💾 Backups/i)).toBeInTheDocument();
    });
  });

  test('can navigate to backups view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/💾 Backups/i));
    });
    // Verify the backup manager is displayed
    await waitFor(() => {
      expect(screen.getByText(/Backup & Disaster Recovery/i)).toBeInTheDocument();
    });
  });

  test('renders rate limits tab for admin users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/🚦 Rate Limits/i)).toBeInTheDocument();
    });
  });

  test('can navigate to rate limits view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/🚦 Rate Limits/i));
    });
    // Verify the rate limits dashboard is displayed
    await waitFor(() => {
      expect(screen.getByText(/API Rate Limiting/i)).toBeInTheDocument();
    });
  });

  test('renders integrations tab for admin users', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/🔌 Integrations/i)).toBeInTheDocument();
    });
  });

  test('can navigate to integrations view', async () => {
    render(<App />);
    await waitFor(() => {
      fireEvent.click(screen.getByText(/🔌 Integrations/i));
    });
    // Verify the integrations manager is displayed
    await waitFor(() => {
      expect(screen.getByText(/External Integrations/i)).toBeInTheDocument();
    });
  });
});
