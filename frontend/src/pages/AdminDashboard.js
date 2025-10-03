import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import '../App.css';

const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('stats');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [parsers, setParsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchUsers();
    fetchParsers();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/admin/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get('/api/admin/users');
      setUsers(response.data.users);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchParsers = async () => {
    try {
      const response = await axios.get('/api/admin/parsers');
      setParsers(response.data.parsers);
    } catch (error) {
      console.error('Failed to fetch parsers:', error);
    }
  };

  const toggleUserStatus = async (userId, isActive) => {
    try {
      await axios.put(`/api/admin/users/${userId}`, {
        is_active: !isActive
      });
      fetchUsers();
    } catch (error) {
      console.error('Failed to update user:', error);
      alert('Failed to update user status');
    }
  };

  const toggleParserAvailability = async (parserId, isAvailable) => {
    try {
      await axios.put(`/api/admin/parsers/${parserId}`, {
        is_available_to_users: !isAvailable
      });
      fetchParsers();
    } catch (error) {
      console.error('Failed to update parser:', error);
      alert('Failed to update parser');
    }
  };

  const makeAdmin = async (userId) => {
    if (!window.confirm('Are you sure you want to make this user an admin?')) {
      return;
    }
    try {
      await axios.put(`/api/admin/users/${userId}`, {
        role: 'admin'
      });
      fetchUsers();
    } catch (error) {
      console.error('Failed to update user:', error);
      alert('Failed to make user admin');
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <div className="header-content">
            <h1>Admin Dashboard</h1>
          </div>
          <div className="header-actions">
            <div className="user-info">
              <span className="username">{user?.username}</span>
              <span className="admin-badge">Admin</span>
            </div>
            <button onClick={() => navigate('/')} className="btn btn-secondary">
              Upload
            </button>
            <button onClick={() => navigate('/history')} className="btn btn-secondary">
              History
            </button>
            <button onClick={logout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </header>

        <div className="card">
          <div className="admin-tabs">
            <button
              className={`admin-tab ${activeTab === 'stats' ? 'active' : ''}`}
              onClick={() => setActiveTab('stats')}
            >
              Statistics
            </button>
            <button
              className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              Users
            </button>
            <button
              className={`admin-tab ${activeTab === 'parsers' ? 'active' : ''}`}
              onClick={() => setActiveTab('parsers')}
            >
              Parsers
            </button>
          </div>

          {activeTab === 'stats' && stats && (
            <div className="admin-content">
              <h2>System Statistics</h2>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{stats.users.total}</div>
                  <div className="stat-label">Total Users</div>
                  <div className="stat-sub">{stats.users.active} active</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.files.total}</div>
                  <div className="stat-label">Total Files</div>
                  <div className="stat-sub">{stats.files.active} active</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.analyses.total}</div>
                  <div className="stat-label">Total Analyses</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.storage.total_mb} MB</div>
                  <div className="stat-label">Storage Used</div>
                  <div className="stat-sub">{(stats.storage.total_mb / 1024).toFixed(2)} GB</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="admin-content">
              <h2>User Management</h2>
              <table className="analysis-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Storage</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td>{u.username}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className={u.role === 'admin' ? 'admin-badge' : 'status-info'}>
                          {u.role}
                        </span>
                      </td>
                      <td>{u.storage_used_mb} / {u.storage_quota_mb} MB</td>
                      <td>
                        <span className={`status-badge ${u.is_active ? 'status-success' : 'status-error'}`}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <div className="action-buttons">
                          <button
                            onClick={() => toggleUserStatus(u.id, u.is_active)}
                            className="btn btn-small"
                          >
                            {u.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                          {u.role !== 'admin' && (
                            <button
                              onClick={() => makeAdmin(u.id)}
                              className="btn btn-small"
                            >
                              Make Admin
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'parsers' && (
            <div className="admin-content">
              <h2>Parser Management</h2>
              <table className="analysis-table">
                <thead>
                  <tr>
                    <th>Parser</th>
                    <th>Key</th>
                    <th>Enabled</th>
                    <th>Available to Users</th>
                    <th>Admin Only</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {parsers.map(p => (
                    <tr key={p.id}>
                      <td>{p.name}</td>
                      <td><code>{p.parser_key}</code></td>
                      <td>
                        <span className={`status-badge ${p.is_enabled ? 'status-success' : 'status-error'}`}>
                          {p.is_enabled ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge ${p.is_available_to_users ? 'status-success' : 'status-error'}`}>
                          {p.is_available_to_users ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge ${p.is_admin_only ? 'status-warning' : 'status-info'}`}>
                          {p.is_admin_only ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        <button
                          onClick={() => toggleParserAvailability(p.id, p.is_available_to_users)}
                          className="btn btn-small"
                        >
                          {p.is_available_to_users ? 'Hide from Users' : 'Show to Users'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
