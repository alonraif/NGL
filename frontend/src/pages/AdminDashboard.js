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
  const [analyses, setAnalyses] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    password: '',
    role: 'user',
    storage_quota_mb: 500
  });

  useEffect(() => {
    fetchStats();
    fetchUsers();
    fetchParsers();
    fetchAnalyses();
  }, []);

  useEffect(() => {
    if (activeTab === 'analyses') {
      fetchAnalyses();
    }
  }, [selectedUserId]);

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

  const fetchAnalyses = async () => {
    try {
      const params = {};
      if (selectedUserId) {
        params.user_id = selectedUserId;
      }
      const response = await axios.get('/api/admin/analyses', { params });
      setAnalyses(response.data.analyses);
    } catch (error) {
      console.error('Failed to fetch analyses:', error);
    }
  };

  const deleteAnalysis = async (analysisId, isHard = false) => {
    const confirmMsg = isHard
      ? 'Are you sure you want to PERMANENTLY delete this analysis? This cannot be undone!'
      : 'Soft delete this analysis? It can be recovered within 90 days.';

    if (!window.confirm(confirmMsg)) return;

    try {
      await axios.delete(`/api/admin/analyses/${analysisId}/delete?type=${isHard ? 'hard' : 'soft'}`);
      fetchAnalyses();
      alert(`Analysis ${isHard ? 'permanently' : 'soft'} deleted successfully`);
    } catch (error) {
      console.error('Failed to delete analysis:', error);
      alert('Failed to delete analysis');
    }
  };

  const bulkDeleteUserAnalyses = async (userId, isHard = false) => {
    const user = users.find(u => u.id === userId);
    const confirmMsg = isHard
      ? `PERMANENTLY delete ALL analyses for user ${user?.username}? This cannot be undone!`
      : `Soft delete ALL analyses for user ${user?.username}? Can be recovered within 90 days.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      await axios.post('/api/admin/analyses/bulk-delete', {
        user_id: userId,
        type: isHard ? 'hard' : 'soft'
      });
      fetchAnalyses();
      alert(`All analyses for user ${user?.username} ${isHard ? 'permanently' : 'soft'} deleted`);
    } catch (error) {
      console.error('Failed to bulk delete:', error);
      alert('Failed to bulk delete analyses');
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

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/admin/users', newUser);
      alert('User created successfully');
      setShowCreateUser(false);
      setNewUser({
        username: '',
        email: '',
        password: '',
        role: 'user',
        storage_quota_mb: 500
      });
      fetchUsers();
    } catch (error) {
      console.error('Failed to create user:', error);
      alert(error.response?.data?.error || 'Failed to create user');
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!window.confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await axios.delete(`/api/admin/users/${userId}`);
      alert('User deleted successfully');
      fetchUsers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      alert(error.response?.data?.error || 'Failed to delete user');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    const password = e.target.new_password.value;
    try {
      await axios.post(`/api/admin/users/${selectedUser.id}/reset-password`, {
        new_password: password
      });
      alert(`Password reset successfully for ${selectedUser.username}`);
      setShowResetPassword(false);
      setSelectedUser(null);
    } catch (error) {
      console.error('Failed to reset password:', error);
      alert(error.response?.data?.error || 'Failed to reset password');
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
            <button
              className={`admin-tab ${activeTab === 'analyses' ? 'active' : ''}`}
              onClick={() => setActiveTab('analyses')}
            >
              Analyses
            </button>
          </div>

          {activeTab === 'stats' && stats && (
            <div className="admin-content">
              <h2>System Statistics</h2>
              <div className="stats-grid">
                <div className="admin-stat-card">
                  <div className="stat-value">{stats.users.total}</div>
                  <div className="stat-label">Total Users</div>
                  <div className="stat-sub">{stats.users.active} active</div>
                </div>
                <div className="admin-stat-card">
                  <div className="stat-value">{stats.files.total}</div>
                  <div className="stat-label">Total Files</div>
                  <div className="stat-sub">{stats.files.active} active</div>
                </div>
                <div className="admin-stat-card">
                  <div className="stat-value">{stats.analyses.total}</div>
                  <div className="stat-label">Total Analyses</div>
                </div>
                <div className="admin-stat-card">
                  <div className="stat-value">{stats.storage.total_mb} MB</div>
                  <div className="stat-label">Storage Used</div>
                  <div className="stat-sub">{(stats.storage.total_mb / 1024).toFixed(2)} GB</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="admin-content">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2>User Management</h2>
                <button
                  onClick={() => setShowCreateUser(true)}
                  className="btn btn-primary"
                >
                  + Create User
                </button>
              </div>

              {showCreateUser && (
                <div className="card" style={{ marginBottom: '20px', background: '#f9fafb' }}>
                  <h3>Create New User</h3>
                  <form onSubmit={handleCreateUser}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                      <div className="form-group">
                        <label>Username *</label>
                        <input
                          type="text"
                          value={newUser.username}
                          onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                          required
                          minLength={3}
                        />
                      </div>
                      <div className="form-group">
                        <label>Email *</label>
                        <input
                          type="email"
                          value={newUser.email}
                          onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Password *</label>
                        <input
                          type="password"
                          value={newUser.password}
                          onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                          required
                          minLength={8}
                        />
                        <small>Min 8 characters, 1 uppercase, 1 lowercase, 1 number</small>
                      </div>
                      <div className="form-group">
                        <label>Role</label>
                        <select
                          value={newUser.role}
                          onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                        >
                          <option value="user">User</option>
                          <option value="admin">Admin</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Storage Quota (MB)</label>
                        <input
                          type="number"
                          value={newUser.storage_quota_mb}
                          onChange={(e) => setNewUser({...newUser, storage_quota_mb: parseInt(e.target.value)})}
                          min={100}
                          max={10000}
                        />
                      </div>
                    </div>
                    <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
                      <button type="submit" className="btn btn-primary">Create User</button>
                      <button
                        type="button"
                        onClick={() => setShowCreateUser(false)}
                        className="btn btn-secondary"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {showResetPassword && selectedUser && (
                <div className="card" style={{ marginBottom: '20px', background: '#fef3c7' }}>
                  <h3>Reset Password for {selectedUser.username}</h3>
                  <form onSubmit={handleResetPassword}>
                    <div className="form-group">
                      <label>New Password *</label>
                      <input
                        type="password"
                        name="new_password"
                        required
                        minLength={8}
                      />
                      <small>Min 8 characters, 1 uppercase, 1 lowercase, 1 number</small>
                    </div>
                    <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
                      <button type="submit" className="btn btn-primary">Reset Password</button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowResetPassword(false);
                          setSelectedUser(null);
                        }}
                        className="btn btn-secondary"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              )}

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
                          <button
                            onClick={() => {
                              setSelectedUser(u);
                              setShowResetPassword(true);
                            }}
                            className="btn btn-small"
                          >
                            Reset Password
                          </button>
                          {u.id !== user.id && (
                            <button
                              onClick={() => handleDeleteUser(u.id, u.username)}
                              className="btn btn-small"
                              style={{ background: '#dc2626', color: 'white' }}
                            >
                              Delete
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

          {activeTab === 'analyses' && (
            <div className="admin-content">
              <h2>Analyses Management</h2>

              <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                <label>Filter by User:</label>
                <select
                  value={selectedUserId || ''}
                  onChange={(e) => setSelectedUserId(e.target.value ? parseInt(e.target.value) : null)}
                  className="form-control"
                  style={{ width: 'auto' }}
                >
                  <option value="">All Users</option>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>{u.username}</option>
                  ))}
                </select>

                {selectedUserId && (
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: '10px' }}>
                    <button
                      onClick={() => bulkDeleteUserAnalyses(selectedUserId, false)}
                      className="btn btn-small btn-warning"
                    >
                      Soft Delete All for User
                    </button>
                    <button
                      onClick={() => bulkDeleteUserAnalyses(selectedUserId, true)}
                      className="btn btn-small btn-danger"
                    >
                      Hard Delete All for User
                    </button>
                  </div>
                )}
              </div>

              <p style={{ marginBottom: '10px' }}>
                Showing {analyses.length} analyses
                {selectedUserId && ` for user ${users.find(u => u.id === selectedUserId)?.username}`}
              </p>

              <table className="analysis-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>User</th>
                    <th>Session Name</th>
                    <th>Parser</th>
                    <th>Filename</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Time</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {analyses.map(a => (
                    <tr key={a.id} className={a.is_deleted ? 'deleted-row' : ''}>
                      <td>{a.id}</td>
                      <td>{a.username}</td>
                      <td>{a.session_name || '-'}</td>
                      <td><code>{a.parse_mode}</code></td>
                      <td>{a.filename || '-'}</td>
                      <td>
                        <span className={`status-badge ${
                          a.status === 'completed' ? 'status-success' :
                          a.status === 'failed' ? 'status-error' :
                          a.status === 'running' ? 'status-warning' : 'status-info'
                        }`}>
                          {a.status}
                        </span>
                        {a.is_deleted && (
                          <span className="status-badge status-error" style={{ marginLeft: '5px' }}>
                            Deleted
                          </span>
                        )}
                      </td>
                      <td>{new Date(a.created_at).toLocaleString()}</td>
                      <td>{a.processing_time_seconds ? `${a.processing_time_seconds}s` : '-'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '5px' }}>
                          <button
                            onClick={() => deleteAnalysis(a.id, false)}
                            className="btn btn-small btn-warning"
                            title="Soft delete (recoverable)"
                          >
                            Soft Del
                          </button>
                          <button
                            onClick={() => deleteAnalysis(a.id, true)}
                            className="btn btn-small btn-danger"
                            title="Permanently delete"
                          >
                            Hard Del
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {analyses.length === 0 && (
                <p style={{ textAlign: 'center', marginTop: '20px', color: '#666' }}>
                  No analyses found{selectedUserId ? ' for this user' : ''}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
