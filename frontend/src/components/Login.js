import React, { useState } from 'react';
import { authApi } from '../api';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await authApi.login(username, password);
      const token = response.data.access_token;
      authApi.setToken(token);

      // Get user info
      const userResponse = await authApi.me();
      authApi.setUser(userResponse.data);

      onLogin(userResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div style={formContainerStyle}>
        <h2 style={{ marginBottom: '20px', textAlign: 'center' }}>
          CEW Training Platform
        </h2>
        <p style={{ color: '#666', textAlign: 'center', marginBottom: '20px' }}>
          Sign in to continue
        </p>

        {error && (
          <div style={errorStyle}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={fieldStyle}>
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={inputStyle}
              placeholder="Enter username"
            />
          </div>

          <div style={fieldStyle}>
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={inputStyle}
              placeholder="Enter password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={buttonStyle}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div style={helpStyle}>
          <small>
            <strong>Demo accounts:</strong><br />
            admin / admin123<br />
            instructor / instructor123<br />
            trainee / trainee123
          </small>
        </div>
      </div>
    </div>
  );
}

const containerStyle = {
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: '100vh',
  backgroundColor: '#f5f5f5',
};

const formContainerStyle = {
  backgroundColor: 'white',
  padding: '40px',
  borderRadius: '8px',
  boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
  width: '100%',
  maxWidth: '400px',
};

const fieldStyle = {
  marginBottom: '16px',
};

const inputStyle = {
  width: '100%',
  padding: '12px',
  fontSize: '14px',
  border: '1px solid #ddd',
  borderRadius: '4px',
  marginTop: '4px',
  boxSizing: 'border-box',
};

const buttonStyle = {
  width: '100%',
  padding: '12px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  fontSize: '16px',
  cursor: 'pointer',
  marginTop: '8px',
};

const errorStyle = {
  backgroundColor: '#f8d7da',
  color: '#721c24',
  padding: '12px',
  borderRadius: '4px',
  marginBottom: '16px',
};

const helpStyle = {
  marginTop: '20px',
  padding: '12px',
  backgroundColor: '#f8f9fa',
  borderRadius: '4px',
  textAlign: 'center',
  color: '#666',
};
