import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import ThemeToggle from '../components/ThemeToggle';
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

  // S3 Storage state
  const [s3Config, setS3Config] = useState(null);
  const [s3Stats, setS3Stats] = useState(null);
  const [s3Form, setS3Form] = useState({
    aws_access_key_id: '',
    aws_secret_access_key: '',
    bucket_name: '',
    region: 'us-east-1',
    server_side_encryption: true
  });
  const [testingS3, setTestingS3] = useState(false);
  const [savingS3, setSavingS3] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchUsers();
    fetchParsers();
    fetchAnalyses();
    fetchS3Config();
    fetchS3Stats();
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

  const fetchS3Config = async () => {
    try {
      const response = await axios.get('/api/admin/s3/config');
      if (response.data.configured) {
        setS3Config(response.data.config);
        setS3Form({
          ...s3Form,
          bucket_name: response.data.config.bucket_name,
          region: response.data.config.region,
          server_side_encryption: response.data.config.server_side_encryption
        });
      }
    } catch (error) {
      console.error('Failed to fetch S3 config:', error);
    }
  };

  const fetchS3Stats = async () => {
    try {
      const response = await axios.get('/api/admin/s3/stats');
      setS3Stats(response.data);
    } catch (error) {
      console.error('Failed to fetch S3 stats:', error);
    }
  };

  const handleSaveS3Config = async (e) => {
    e.preventDefault();
    setSavingS3(true);
    try {
      await axios.put('/api/admin/s3/config', s3Form);
      alert('S3 configuration saved successfully');
      fetchS3Config();
      fetchS3Stats();
    } catch (error) {
      console.error('Failed to save S3 config:', error);
      alert(error.response?.data?.error || 'Failed to save S3 configuration');
    } finally {
      setSavingS3(false);
    }
  };

  const handleTestS3 = async () => {
    setTestingS3(true);
    try {
      const response = await axios.post('/api/admin/s3/test');
      if (response.data.success) {
        alert('✓ ' + response.data.message);
      } else {
        alert('✗ ' + response.data.message);
      }
      fetchS3Config();
    } catch (error) {
      console.error('Failed to test S3:', error);
      alert('✗ Connection test failed: ' + (error.response?.data?.message || error.message));
    } finally {
      setTestingS3(false);
    }
  };

  const handleToggleS3 = async (enable) => {
    try {
      if (enable) {
        const response = await axios.post('/api/admin/s3/enable');
        alert(response.data.message);
      } else {
        const response = await axios.post('/api/admin/s3/disable');
        alert(response.data.message);
      }
      fetchS3Config();
      fetchS3Stats();
    } catch (error) {
      console.error('Failed to toggle S3:', error);
      alert(error.response?.data?.error || error.response?.data?.message || 'Failed to toggle S3 storage');
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
            <ThemeToggle />
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
            <button
              className={`admin-tab ${activeTab === 's3' ? 'active' : ''}`}
              onClick={() => setActiveTab('s3')}
            >
              S3 Storage
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

              {s3Stats && s3Stats.storage && (
                <div style={{ marginTop: '30px' }}>
                  <h3 style={{ marginBottom: '15px' }}>Storage Distribution</h3>
                  <div className="card" style={{ background: '#f9fafb' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                          <h4 style={{ margin: 0 }}>S3 Storage</h4>
                          <span style={{
                            padding: '4px 12px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            fontWeight: '600',
                            background: s3Stats.storage_mode === 's3' ? '#dbeafe' : '#e5e7eb',
                            color: s3Stats.storage_mode === 's3' ? '#1e40af' : '#6b7280'
                          }}>
                            {s3Stats.storage_mode === 's3' ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                        <div className="admin-stat-card" style={{ marginBottom: '10px' }}>
                          <div className="stat-value">{s3Stats.files.s3 || 0}</div>
                          <div className="stat-label">Files in S3</div>
                          <div className="stat-sub">{Number(s3Stats.storage.s3.gb || 0).toFixed(2)} GB</div>
                        </div>
                        <div style={{ height: '20px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${Number(s3Stats.storage.s3.percentage || 0)}%`,
                            height: '100%',
                            background: 'linear-gradient(90deg, #3b82f6, #2563eb)',
                            transition: 'width 0.3s ease'
                          }}></div>
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '13px', color: '#6b7280' }}>
                          {Number(s3Stats.storage.s3.percentage || 0).toFixed(1)}% of total storage
                        </div>
                      </div>
                      <div>
                        <h4 style={{ marginBottom: '10px' }}>Local Storage</h4>
                        <div className="admin-stat-card" style={{ marginBottom: '10px' }}>
                          <div className="stat-value">{s3Stats.files.local || 0}</div>
                          <div className="stat-label">Files in Local</div>
                          <div className="stat-sub">{Number(s3Stats.storage.local.gb || 0).toFixed(2)} GB</div>
                        </div>
                        <div style={{ height: '20px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${Number(s3Stats.storage.local.percentage || 0)}%`,
                            height: '100%',
                            background: 'linear-gradient(90deg, #6b7280, #4b5563)',
                            transition: 'width 0.3s ease'
                          }}></div>
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '13px', color: '#6b7280' }}>
                          {Number(s3Stats.storage.local.percentage || 0).toFixed(1)}% of total storage
                        </div>
                      </div>
                    </div>
                    <div style={{
                      marginTop: '20px',
                      padding: '15px',
                      background: '#f3f4f6',
                      borderRadius: '6px',
                      borderLeft: '4px solid #3b82f6'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <strong style={{ fontSize: '14px' }}>Total Storage Across All Locations</strong>
                          <div style={{ marginTop: '4px', fontSize: '13px', color: '#6b7280' }}>
                            {s3Stats.files.total || 0} files
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '24px', fontWeight: '700', color: '#1f2937' }}>
                            {Number(s3Stats.storage.total.gb || 0).toFixed(2)} GB
                          </div>
                          <div style={{ fontSize: '12px', color: '#6b7280' }}>
                            {Number(s3Stats.storage.total.mb || 0).toFixed(0)} MB
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
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
                    <th>Storage</th>
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
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: '500',
                          background: a.storage_type === 's3' ? '#dbeafe' : '#e5e7eb',
                          color: a.storage_type === 's3' ? '#1e40af' : '#374151'
                        }}>
                          {a.storage_type === 's3' ? '☁️ S3' : '🗄️ Local'}
                        </span>
                      </td>
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

          {activeTab === 's3' && (
            <div className="admin-content">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div>
                  <h2 style={{ margin: 0 }}>Amazon S3 Storage</h2>
                  <p style={{ margin: '4px 0 0 0', color: '#6b7280', fontSize: '14px' }}>
                    Configure cloud storage for uploaded log files
                  </p>
                </div>
                {s3Config && s3Config.last_test_success && (
                  <span className="status-badge status-success" style={{ fontSize: '13px' }}>
                    {s3Config.is_enabled ? 'S3 Active' : 'S3 Configured'}
                  </span>
                )}
              </div>

              {/* Connection Status Card */}
              {s3Config && (
                <div className="card" style={{
                  marginBottom: '20px',
                  background: s3Config.is_enabled ? '#ecfdf5' : '#f9fafb',
                  border: s3Config.is_enabled ? '1px solid #10b981' : '1px solid #e5e7eb'
                }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                        Storage Mode
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: '600', color: '#111827' }}>
                        {s3Stats?.storage_mode === 's3' ? 'Amazon S3' : 'Local Storage'}
                      </div>
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        {s3Config.is_enabled ? 'Active and receiving uploads' : 'Inactive'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                        Connection Status
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: '600', color: s3Config.last_test_success ? '#059669' : '#dc2626' }}>
                        {s3Config.last_test_success ? 'Connected' : 'Disconnected'}
                      </div>
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        {s3Config.last_test_at ? `Tested ${new Date(s3Config.last_test_at).toLocaleDateString()}` : 'Never tested'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                        Bucket
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: '600', color: '#111827' }}>
                        {s3Config.bucket_name}
                      </div>
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        {s3Config.region}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Storage Distribution */}
              {s3Stats && s3Stats.storage && (
                <div className="card" style={{ marginBottom: '20px' }}>
                  <h3 style={{ marginBottom: '20px', fontSize: '16px', fontWeight: '600' }}>Storage Distribution</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: '#6b7280', marginBottom: '4px' }}>Amazon S3</div>
                          <div style={{ fontSize: '24px', fontWeight: '700', color: '#111827' }}>
                            {Number(s3Stats.storage.s3.gb || 0).toFixed(2)} <span style={{ fontSize: '14px', fontWeight: '500', color: '#6b7280' }}>GB</span>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '20px', fontWeight: '700', color: '#3b82f6' }}>
                            {Number(s3Stats.storage.s3.percentage || 0).toFixed(1)}%
                          </div>
                          <div style={{ fontSize: '12px', color: '#6b7280' }}>
                            {s3Stats.files.s3 || 0} files
                          </div>
                        </div>
                      </div>
                      <div style={{ height: '8px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${Number(s3Stats.storage.s3.percentage || 0)}%`,
                          height: '100%',
                          background: 'linear-gradient(90deg, #3b82f6, #2563eb)',
                          transition: 'width 0.3s ease'
                        }}></div>
                      </div>
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: '#6b7280', marginBottom: '4px' }}>Local Storage</div>
                          <div style={{ fontSize: '24px', fontWeight: '700', color: '#111827' }}>
                            {Number(s3Stats.storage.local.gb || 0).toFixed(2)} <span style={{ fontSize: '14px', fontWeight: '500', color: '#6b7280' }}>GB</span>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '20px', fontWeight: '700', color: '#6b7280' }}>
                            {Number(s3Stats.storage.local.percentage || 0).toFixed(1)}%
                          </div>
                          <div style={{ fontSize: '12px', color: '#6b7280' }}>
                            {s3Stats.files.local || 0} files
                          </div>
                        </div>
                      </div>
                      <div style={{ height: '8px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${Number(s3Stats.storage.local.percentage || 0)}%`,
                          height: '100%',
                          background: 'linear-gradient(90deg, #6b7280, #4b5563)',
                          transition: 'width 0.3s ease'
                        }}></div>
                      </div>
                    </div>
                  </div>
                  <div style={{
                    marginTop: '20px',
                    padding: '16px',
                    background: '#f9fafb',
                    borderRadius: '6px',
                    borderLeft: '3px solid #3b82f6',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '600', color: '#6b7280' }}>Total Storage</div>
                      <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
                        {s3Stats.files.total || 0} files across all locations
                      </div>
                    </div>
                    <div style={{ fontSize: '28px', fontWeight: '700', color: '#111827' }}>
                      {Number(s3Stats.storage.total.gb || 0).toFixed(2)} <span style={{ fontSize: '16px', fontWeight: '500', color: '#6b7280' }}>GB</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Configuration Form */}
              <div className="card" style={{ marginBottom: '20px' }}>
                <h3 style={{ marginBottom: '20px', fontSize: '16px', fontWeight: '600' }}>AWS Credentials & Configuration</h3>
                <form onSubmit={handleSaveS3Config}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <div className="form-group">
                      <label style={{ fontWeight: '500', marginBottom: '8px', display: 'block' }}>AWS Access Key ID *</label>
                      <input
                        type="text"
                        value={s3Form.aws_access_key_id}
                        onChange={(e) => setS3Form({...s3Form, aws_access_key_id: e.target.value})}
                        placeholder={s3Config?.aws_access_key_id || 'AKIAIOSFODNN7EXAMPLE'}
                        required
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div className="form-group">
                      <label style={{ fontWeight: '500', marginBottom: '8px', display: 'block' }}>AWS Secret Access Key *</label>
                      <input
                        type="password"
                        value={s3Form.aws_secret_access_key}
                        onChange={(e) => setS3Form({...s3Form, aws_secret_access_key: e.target.value})}
                        placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                        required
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div className="form-group">
                      <label style={{ fontWeight: '500', marginBottom: '8px', display: 'block' }}>S3 Bucket Name *</label>
                      <input
                        type="text"
                        value={s3Form.bucket_name}
                        onChange={(e) => setS3Form({...s3Form, bucket_name: e.target.value})}
                        placeholder="my-ngl-logs-bucket"
                        required
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div className="form-group">
                      <label style={{ fontWeight: '500', marginBottom: '8px', display: 'block' }}>AWS Region *</label>
                      <select
                        value={s3Form.region}
                        onChange={(e) => setS3Form({...s3Form, region: e.target.value})}
                        style={{ width: '100%' }}
                      >
                        <option value="us-east-1">US East (N. Virginia) - us-east-1</option>
                        <option value="us-east-2">US East (Ohio) - us-east-2</option>
                        <option value="us-west-1">US West (N. California) - us-west-1</option>
                        <option value="us-west-2">US West (Oregon) - us-west-2</option>
                        <option value="eu-west-1">EU (Ireland) - eu-west-1</option>
                        <option value="eu-central-1">EU (Frankfurt) - eu-central-1</option>
                        <option value="ap-southeast-1">Asia Pacific (Singapore) - ap-southeast-1</option>
                        <option value="ap-northeast-1">Asia Pacific (Tokyo) - ap-northeast-1</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-group" style={{ marginTop: '20px', padding: '16px', background: '#f9fafb', borderRadius: '6px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', margin: 0 }}>
                      <input
                        type="checkbox"
                        checked={s3Form.server_side_encryption}
                        onChange={(e) => setS3Form({...s3Form, server_side_encryption: e.target.checked})}
                        style={{ marginRight: '10px', width: '16px', height: '16px' }}
                      />
                      <span style={{ fontWeight: '500' }}>Enable Server-Side Encryption (AES-256)</span>
                    </label>
                    <div style={{ marginLeft: '26px', marginTop: '8px', fontSize: '13px', color: '#6b7280' }}>
                      Encrypts files at rest in S3. Recommended for sensitive data.
                    </div>
                  </div>
                  <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '12px' }}>
                    <button type="submit" className="btn btn-primary" disabled={savingS3}>
                      {savingS3 ? 'Saving Configuration...' : 'Save Configuration'}
                    </button>
                    <button
                      type="button"
                      onClick={handleTestS3}
                      className="btn btn-secondary"
                      disabled={testingS3 || !s3Config}
                    >
                      {testingS3 ? 'Testing Connection...' : 'Test Connection'}
                    </button>
                    {s3Config && (
                      <button
                        type="button"
                        onClick={() => handleToggleS3(!s3Config.is_enabled)}
                        className={`btn ${s3Config.is_enabled ? 'btn-warning' : 'btn-success'}`}
                        disabled={!s3Config.last_test_success && !s3Config.is_enabled}
                        style={{ marginLeft: 'auto' }}
                      >
                        {s3Config.is_enabled ? 'Disable S3 Storage' : 'Enable S3 Storage'}
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Information Panel */}
              <div className="card" style={{ background: '#f9fafb', border: '1px solid #e5e7eb' }}>
                <h3 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '600' }}>Integration Details</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', fontSize: '14px' }}>
                  <div>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '12px' }}>How It Works</h4>
                    <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8', color: '#6b7280' }}>
                      <li>When enabled, new uploads are automatically stored in Amazon S3</li>
                      <li>Automatic fallback to local storage if S3 becomes unavailable</li>
                      <li>Existing files remain in their current storage location</li>
                      <li>Downloads are seamless regardless of storage location</li>
                    </ul>
                  </div>
                  <div>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '12px' }}>Required IAM Permissions</h4>
                    <div style={{ background: '#fff', padding: '12px', borderRadius: '4px', border: '1px solid #e5e7eb' }}>
                      <code style={{ fontSize: '12px', color: '#374151', display: 'block', lineHeight: '1.6' }}>
                        s3:PutObject<br/>
                        s3:GetObject<br/>
                        s3:DeleteObject
                      </code>
                    </div>
                  </div>
                </div>
                <div style={{ marginTop: '20px', padding: '12px 16px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '6px', fontSize: '13px', color: '#1e40af' }}>
                  <strong>Security:</strong> All files are encrypted at rest with AES-256. Download URLs are time-limited and expire after 1 hour.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
