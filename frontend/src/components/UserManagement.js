import React, { useState, useEffect } from 'react';
import { userApi } from '../api';

const INITIAL_USER_STATE = {
  username: '',
  password: '',
  email: '',
  full_name: '',
  role: 'trainee',
};

export default function UserManagement({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUser, setNewUser] = useState(INITIAL_USER_STATE);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await userApi.list();
      setUsers(response.data);
      setError(null);
    } catch (err) {
      if (err.response?.status === 403) {
        setError('Permission denied. Admin access required.');
      } else {
        setError('Failed to load users');
      }
      console.error('Error loading users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await userApi.create(newUser);
      setMessage('User created successfully');
      setShowCreateForm(false);
      setNewUser(INITIAL_USER_STATE);
      loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleDeleteUser = async (username) => {
    if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }

    try {
      await userApi.delete(username);
      setMessage(`User "${username}" deleted successfully`);
      loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete user');
    }
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin': return '#dc3545';
      case 'instructor': return '#17a2b8';
      case 'trainee': return '#28a745';
      default: return '#6c757d';
    }
  };

  // Only admins can access this component
  if (currentUser?.role !== 'admin') {
    return (
      <div style={containerStyle}>
        <h2>👥 User Management</h2>
        <p style={{ color: '#dc3545' }}>Admin access required.</p>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>👥 User Management</h2>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          style={btnPrimaryStyle}
        >
          {showCreateForm ? '✕ Cancel' : '+ Add User'}
        </button>
      </div>

      {error && <div style={errorStyle}>{error}</div>}
      {message && <div style={successStyle}>{message}</div>}

      {/* Create User Form */}
      {showCreateForm && (
        <div style={formContainerStyle}>
          <h3>Create New User</h3>
          <form onSubmit={handleCreateUser} style={formStyle}>
            <div style={formRowStyle}>
              <label style={labelStyle}>Username *</label>
              <input
                type="text"
                value={newUser.username}
                onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                required
                style={inputStyle}
              />
            </div>
            <div style={formRowStyle}>
              <label style={labelStyle}>Password *</label>
              <input
                type="password"
                value={newUser.password}
                onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                required
                style={inputStyle}
              />
            </div>
            <div style={formRowStyle}>
              <label style={labelStyle}>Full Name</label>
              <input
                type="text"
                value={newUser.full_name}
                onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                style={inputStyle}
              />
            </div>
            <div style={formRowStyle}>
              <label style={labelStyle}>Email</label>
              <input
                type="email"
                value={newUser.email}
                onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                style={inputStyle}
              />
            </div>
            <div style={formRowStyle}>
              <label style={labelStyle}>Role *</label>
              <select
                value={newUser.role}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                style={inputStyle}
              >
                <option value="trainee">Trainee</option>
                <option value="instructor">Instructor</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div style={{ marginTop: '16px' }}>
              <button type="submit" style={btnPrimaryStyle}>
                Create User
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      {loading ? (
        <p>Loading users...</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Username</th>
              <th style={thStyle}>Full Name</th>
              <th style={thStyle}>Email</th>
              <th style={thStyle}>Role</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.username}>
                <td style={tdStyle}>
                  <strong>{user.username}</strong>
                  {user.username === currentUser.username && (
                    <span style={{ color: '#666', fontSize: '12px', marginLeft: '8px' }}>(you)</span>
                  )}
                </td>
                <td style={tdStyle}>{user.full_name || '-'}</td>
                <td style={tdStyle}>{user.email || '-'}</td>
                <td style={tdStyle}>
                  <span style={{ ...roleBadgeStyle, backgroundColor: getRoleBadgeColor(user.role) }}>
                    {user.role}
                  </span>
                </td>
                <td style={tdStyle}>
                  {user.username !== currentUser.username ? (
                    <button
                      onClick={() => handleDeleteUser(user.username)}
                      style={btnDangerStyle}
                    >
                      Delete
                    </button>
                  ) : (
                    <span style={{ color: '#999', fontSize: '12px' }}>Cannot delete self</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const containerStyle = {
  padding: '20px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  marginBottom: '20px',
};

const formContainerStyle = {
  backgroundColor: 'white',
  padding: '20px',
  borderRadius: '8px',
  marginBottom: '20px',
  border: '1px solid #ddd',
};

const formStyle = {
  display: 'grid',
  gap: '12px',
};

const formRowStyle = {
  display: 'grid',
  gridTemplateColumns: '120px 1fr',
  alignItems: 'center',
  gap: '12px',
};

const labelStyle = {
  fontWeight: '500',
  fontSize: '14px',
};

const inputStyle = {
  padding: '8px 12px',
  border: '1px solid #ddd',
  borderRadius: '4px',
  fontSize: '14px',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  backgroundColor: 'white',
};

const thStyle = {
  border: '1px solid #ddd',
  padding: '12px',
  backgroundColor: '#f4f4f4',
  textAlign: 'left',
  fontWeight: '600',
};

const tdStyle = {
  border: '1px solid #ddd',
  padding: '12px',
};

const roleBadgeStyle = {
  padding: '4px 10px',
  borderRadius: '12px',
  color: 'white',
  fontSize: '12px',
  fontWeight: '500',
  textTransform: 'uppercase',
};

const btnPrimaryStyle = {
  padding: '8px 16px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const btnDangerStyle = {
  padding: '6px 12px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const errorStyle = {
  backgroundColor: '#f8d7da',
  color: '#721c24',
  padding: '12px',
  borderRadius: '4px',
  marginBottom: '16px',
};

const successStyle = {
  backgroundColor: '#d4edda',
  color: '#155724',
  padding: '12px',
  borderRadius: '4px',
  marginBottom: '16px',
};
