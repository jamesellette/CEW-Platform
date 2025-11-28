import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

// Mock the API module to avoid network requests in tests
jest.mock('./api', () => ({
  scenarioApi: {
    list: jest.fn().mockResolvedValue({ data: [] }),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
  },
}));

test('renders platform title', async () => {
  render(<App />);
  expect(screen.getByText(/CEW Training Platform/i)).toBeInTheDocument();
  // Wait for async operations to complete
  await waitFor(() => {
    expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument();
  });
});

test('renders create scenario button', async () => {
  render(<App />);
  expect(screen.getByText(/Create New Scenario/i)).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument();
  });
});

test('renders safety warning in footer', async () => {
  render(<App />);
  expect(screen.getByText(/Training use only/i)).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument();
  });
});
