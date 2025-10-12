import React, { useState, useEffect, useCallback } from 'react';
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

  const theme = {
    bgCard: 'var(--bg-card)',
    bgSecondary: 'var(--bg-secondary)',
    bgTertiary: 'var(--bg-tertiary)',
    bgHover: 'var(--bg-hover)',
    border: 'var(--border-color)',
    borderStrong: 'var(--border-strong)',
    textPrimary: 'var(--text-primary)',
    textSecondary: 'var(--text-secondary)',
    textTertiary: 'var(--text-tertiary)',
    brandPrimary: 'var(--brand-primary)',
    brandPrimaryHover: 'var(--brand-primary-hover)',
    brandGradient: 'linear-gradient(90deg, var(--brand-primary), var(--brand-primary-hover))',
    neutralGradient: 'linear-gradient(90deg, var(--text-secondary), var(--text-primary))',
    success: 'var(--success)',
    successBg: 'var(--success-bg)',
    successLight: 'var(--success-light)',
    warning: 'var(--warning)',
    warningBg: 'var(--warning-bg)',
    error: 'var(--error)',
    errorBg: 'var(--error-bg)',
    info: 'var(--info)',
    infoBg: 'var(--info-bg)',
    infoLight: 'var(--info-light)',
    shadow: 'var(--shadow-color)',
    codeBg: 'var(--code-bg)',
    codeText: 'var(--code-text)'
  };

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

  // SSL configuration state
  const [sslConfig, setSslConfig] = useState(null);
  const [sslLoading, setSslLoading] = useState(true);
  const [sslProcessing, setSslProcessing] = useState(false);
  const [sslSettingsForm, setSslSettingsForm] = useState({
    mode: 'lets_encrypt',
    primary_domain: '',
    alternate_domains: '',
    verification_hostname: '',
    auto_renew: true
  });
  const [sslUploadForm, setSslUploadForm] = useState({
    certificate_file: null,
    private_key_file: null
  });
  const [sslMessage, setSslMessage] = useState(null);
  const [sslError, setSslError] = useState(null);

  const fetchSslConfig = useCallback(async (showSpinner = true) => {
    try {
      if (showSpinner) {
        setSslLoading(true);
      }
      const response = await axios.get('/api/admin/ssl');
      const ssl = response.data?.ssl || null;
      setSslConfig(ssl);
      if (ssl) {
        setSslSettingsForm({
          mode: ssl.mode || 'lets_encrypt',
          primary_domain: ssl.primary_domain || '',
          alternate_domains: (ssl.alternate_domains || []).join(', '),
          verification_hostname: ssl.verification_hostname || '',
          auto_renew: ssl.auto_renew !== false
        });
      }
    } catch (error) {
      console.error('Failed to fetch SSL config:', error);
      setSslError(error.response?.data?.error || 'Failed to load SSL configuration');
    } finally {
      if (showSpinner) {
        setSslLoading(false);
      }
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get('/api/admin/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const response = await axios.get('/api/admin/users');
      setUsers(response.data.users);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchParsers = useCallback(async () => {
    try {
      const response = await axios.get('/api/admin/parsers');
      setParsers(response.data.parsers);
    } catch (error) {
      console.error('Failed to fetch parsers:', error);
    }
  }, []);

  const fetchAnalyses = useCallback(async () => {
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
  }, [selectedUserId]);

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

  const handleSslSettingsChange = (field, value) => {
    setSslSettingsForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const submitSslSettings = async (e) => {
    e?.preventDefault();
    setSslProcessing(true);
    setSslMessage(null);
    setSslError(null);
    try {
      const payload = {
        mode: sslSettingsForm.mode,
        primary_domain: sslSettingsForm.primary_domain.trim() || null,
        alternate_domains: sslSettingsForm.alternate_domains
          ? sslSettingsForm.alternate_domains.split(',').map(d => d.trim()).filter(Boolean)
          : [],
        verification_hostname: sslSettingsForm.verification_hostname.trim() || null,
        auto_renew: sslSettingsForm.auto_renew
      };
      const response = await axios.post('/api/admin/ssl/settings', payload);
      setSslConfig(response.data?.ssl);
      setSslMessage('SSL settings updated');
    } catch (error) {
      console.error('Failed to update SSL settings:', error);
      setSslError(error.response?.data?.error || 'Failed to update SSL settings');
    } finally {
      setSslProcessing(false);
    }
  };

  const submitSslUpload = async (e) => {
    e?.preventDefault();
    if (!sslUploadForm.certificate_file || !sslUploadForm.private_key_file) {
      setSslError('Please select both certificate and private key files.');
      return;
    }
    setSslProcessing(true);
    setSslMessage(null);
    setSslError(null);
    try {
      const formData = new FormData();
      formData.append('certificate_file', sslUploadForm.certificate_file);
      formData.append('private_key_file', sslUploadForm.private_key_file);
      // Certificate file should already include intermediates (full chain)
      const response = await axios.post('/api/admin/ssl/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSslConfig(response.data?.ssl);
      setSslMessage('Certificate uploaded successfully');
      setSslUploadForm({ certificate_file: null, private_key_file: null });
      fetchSslConfig();
    } catch (error) {
      console.error('Failed to upload certificate:', error);
      setSslError(error.response?.data?.error || 'Failed to upload certificate');
    } finally {
      setSslProcessing(false);
    }
  };

  const triggerIssuance = async () => {
    if (!window.confirm('Start Let\'s Encrypt issuance? Ensure DNS points to this host first.')) {
      return;
    }
    setSslProcessing(true);
    setSslMessage(null);
    setSslError(null);
    try {
      const response = await axios.post('/api/admin/ssl/issue', {});
      setSslMessage(response.data?.message || 'Issuance started');
      fetchSslConfig();
    } catch (error) {
      console.error('Failed to start issuance:', error);
      setSslError(error.response?.data?.error || 'Failed to start issuance');
    } finally {
      setSslProcessing(false);
    }
  };

  const triggerRenewal = async () => {
    setSslProcessing(true);
    setSslMessage(null);
    setSslError(null);
    try {
      const response = await axios.post('/api/admin/ssl/renew', {});
      setSslMessage(response.data?.message || 'Renewal started');
      fetchSslConfig();
    } catch (error) {
      console.error('Failed to start renewal:', error);
      setSslError(error.response?.data?.error || 'Failed to start renewal');
    } finally {
      setSslProcessing(false);
    }
  };

  const toggleHttpsEnforcement = async (enforce) => {
    setSslProcessing(true);
    setSslMessage(null);
    setSslError(null);
    try {
      const response = await axios.post('/api/admin/ssl/enforce', { enforce });
      setSslConfig(response.data?.ssl);
      setSslMessage(enforce ? 'HTTPS enforced' : 'HTTPS disabled');
    } catch (error) {
      console.error('Failed to toggle HTTPS enforcement:', error);
      setSslError(error.response?.data?.error || 'Failed to toggle HTTPS enforcement');
    } finally {
      setSslProcessing(false);
    }
  };

  const triggerSslHealthCheck = async () => {
    setSslProcessing(true);
    setSslMessage(null);
    setSslError(null);
    try {
      await axios.post('/api/admin/ssl/health-check', {});
      setSslMessage('Health check scheduled');
      await fetchSslConfig(false);
      setTimeout(() => fetchSslConfig(false), 3000);
      setTimeout(() => fetchSslConfig(false), 6000);
    } catch (error) {
      console.error('Failed to queue health check:', error);
      setSslError(error.response?.data?.error || 'Failed to queue health check');
    } finally {
      setSslProcessing(false);
    }
  };

  const handleSslFileChange = (field, files) => {
    const file = files && files.length > 0 ? files[0] : null;
    setSslUploadForm(prev => ({
      ...prev,
      [field]: file
    }));
  };

  const currentSslMode = sslSettingsForm.mode || 'lets_encrypt';
  const isLetsEncryptMode = currentSslMode === 'lets_encrypt';
  const sslStatusLabel = sslConfig?.certificate_status || 'idle';
  const canEnforceHttps = Boolean(
    sslConfig && (
      (sslConfig.mode === 'lets_encrypt' && sslConfig.certificate_status === 'verified') ||
      (sslConfig.mode === 'uploaded' && sslConfig.uploaded?.available)
    )
  );
  const formatDateTime = (value) => (value ? new Date(value).toLocaleString() : '—');

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

  const fetchS3Config = useCallback(async () => {
    try {
      const response = await axios.get('/api/admin/s3/config');
      if (response.data.configured) {
        setS3Config(response.data.config);
        setS3Form(prev => ({
          ...prev,
          bucket_name: response.data.config.bucket_name,
          region: response.data.config.region,
          server_side_encryption: response.data.config.server_side_encryption
        }));
      }
    } catch (error) {
      console.error('Failed to fetch S3 config:', error);
    }
  }, []);

  const fetchS3Stats = useCallback(async () => {
    try {
      const response = await axios.get('/api/admin/s3/stats');
      setS3Stats(response.data);
    } catch (error) {
      console.error('Failed to fetch S3 stats:', error);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchUsers();
    fetchParsers();
    fetchAnalyses();
    fetchS3Config();
    fetchS3Stats();
    fetchSslConfig();
  }, [fetchStats, fetchUsers, fetchParsers, fetchAnalyses, fetchS3Config, fetchS3Stats, fetchSslConfig]);

  useEffect(() => {
    if (activeTab === 'analyses') {
      fetchAnalyses();
    }
  }, [activeTab, fetchAnalyses]);

  const sslStatus = sslConfig?.certificate_status;

  useEffect(() => {
    const pollStatuses = ['pending_issue', 'renewing'];
    if (!sslStatus || !pollStatuses.includes(sslStatus)) {
      return undefined;
    }
    const intervalId = setInterval(() => {
      fetchSslConfig(false);
    }, 5000);
    return () => clearInterval(intervalId);
  }, [sslStatus, fetchSslConfig]);

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
            <button
              className={`admin-tab ${activeTab === 'ssl' ? 'active' : ''}`}
              onClick={() => setActiveTab('ssl')}
            >
              SSL
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
                  <div className="card" style={{ background: theme.bgTertiary }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                          <h4 style={{ margin: 0 }}>S3 Storage</h4>
                          <span style={{
                            padding: '4px 12px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            fontWeight: '600',
                            background: s3Stats.storage_mode === 's3' ? theme.infoBg : theme.bgHover,
                            color: s3Stats.storage_mode === 's3' ? theme.info : theme.textSecondary
                          }}>
                            {s3Stats.storage_mode === 's3' ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                        <div className="admin-stat-card" style={{ marginBottom: '10px' }}>
                          <div className="stat-value">{s3Stats.files.s3 || 0}</div>
                          <div className="stat-label">Files in S3</div>
                          <div className="stat-sub">{Number(s3Stats.storage.s3.gb || 0).toFixed(2)} GB</div>
                        </div>
                        <div style={{ height: '20px', background: theme.bgHover, borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${Number(s3Stats.storage.s3.percentage || 0)}%`,
                            height: '100%',
                            background: theme.brandGradient,
                            transition: 'width 0.3s ease'
                          }}></div>
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '13px', color: theme.textSecondary }}>
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
                        <div style={{ height: '20px', background: theme.bgHover, borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${Number(s3Stats.storage.local.percentage || 0)}%`,
                            height: '100%',
                            background: theme.neutralGradient,
                            transition: 'width 0.3s ease'
                          }}></div>
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '13px', color: theme.textSecondary }}>
                          {Number(s3Stats.storage.local.percentage || 0).toFixed(1)}% of total storage
                        </div>
                      </div>
                    </div>
                    <div style={{
                      marginTop: '20px',
                      padding: '15px',
                      background: theme.bgHover,
                      borderRadius: '6px',
                      borderLeft: `4px solid ${theme.brandPrimary}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <strong style={{ fontSize: '14px' }}>Total Storage Across All Locations</strong>
                          <div style={{ marginTop: '4px', fontSize: '13px', color: theme.textSecondary }}>
                            {s3Stats.files.total || 0} files
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '24px', fontWeight: '700', color: theme.textPrimary }}>
                            {Number(s3Stats.storage.total.gb || 0).toFixed(2)} GB
                          </div>
                          <div style={{ fontSize: '12px', color: theme.textSecondary }}>
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
                <div className="card" style={{ marginBottom: '20px', background: theme.bgTertiary }}>
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
                <div className="card" style={{ marginBottom: '20px', background: theme.warningBg, border: `1px solid ${theme.warning}` }}>
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
                              style={{ background: theme.error, color: 'white' }}
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
                          background: a.storage_type === 's3' ? theme.infoBg : theme.bgHover,
                          color: a.storage_type === 's3' ? theme.info : theme.textPrimary
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
                <p style={{ textAlign: 'center', marginTop: '20px', color: theme.textSecondary }}>
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
                  <p style={{ margin: '4px 0 0 0', color: theme.textSecondary, fontSize: '14px' }}>
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
                  background: s3Config.is_enabled ? theme.successLight : theme.bgTertiary,
                  border: s3Config.is_enabled ? `1px solid ${theme.success}` : `1px solid ${theme.border}`
                }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: theme.textSecondary, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                        Storage Mode
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: '600', color: theme.textPrimary }}>
                        {s3Stats?.storage_mode === 's3' ? 'Amazon S3' : 'Local Storage'}
                      </div>
                      <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                        {s3Config.is_enabled ? 'Active and receiving uploads' : 'Inactive'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: theme.textSecondary, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                        Connection Status
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: '600', color: s3Config.last_test_success ? theme.success : theme.error }}>
                        {s3Config.last_test_success ? 'Connected' : 'Disconnected'}
                      </div>
                      <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                        {s3Config.last_test_at ? `Tested ${new Date(s3Config.last_test_at).toLocaleDateString()}` : 'Never tested'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: theme.textSecondary, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                        Bucket
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: '600', color: theme.textPrimary }}>
                        {s3Config.bucket_name}
                      </div>
                      <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                        {s3Config.region}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Storage Distribution */}
              {s3Stats && s3Stats.storage && (
                <div className="card" style={{ marginBottom: '20px' }}>
                  <h3 style={{ marginBottom: '20px', fontSize: '16px', fontWeight: '600', color: theme.textPrimary }}>Storage Distribution</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: theme.textSecondary, marginBottom: '4px' }}>Amazon S3</div>
                          <div style={{ fontSize: '24px', fontWeight: '700', color: theme.textPrimary }}>
                            {Number(s3Stats.storage.s3.gb || 0).toFixed(2)} <span style={{ fontSize: '14px', fontWeight: '500', color: theme.textSecondary }}>GB</span>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '20px', fontWeight: '700', color: theme.info }}>
                            {Number(s3Stats.storage.s3.percentage || 0).toFixed(1)}%
                          </div>
                          <div style={{ fontSize: '12px', color: theme.textSecondary }}>
                            {s3Stats.files.s3 || 0} files
                          </div>
                        </div>
                      </div>
                      <div style={{ height: '8px', background: theme.bgHover, borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${Number(s3Stats.storage.s3.percentage || 0)}%`,
                          height: '100%',
                          background: theme.brandGradient,
                          transition: 'width 0.3s ease'
                        }}></div>
                      </div>
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: theme.textSecondary, marginBottom: '4px' }}>Local Storage</div>
                          <div style={{ fontSize: '24px', fontWeight: '700', color: theme.textPrimary }}>
                            {Number(s3Stats.storage.local.gb || 0).toFixed(2)} <span style={{ fontSize: '14px', fontWeight: '500', color: theme.textSecondary }}>GB</span>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '20px', fontWeight: '700', color: theme.textSecondary }}>
                            {Number(s3Stats.storage.local.percentage || 0).toFixed(1)}%
                          </div>
                          <div style={{ fontSize: '12px', color: theme.textSecondary }}>
                            {s3Stats.files.local || 0} files
                          </div>
                        </div>
                      </div>
                      <div style={{ height: '8px', background: theme.bgHover, borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${Number(s3Stats.storage.local.percentage || 0)}%`,
                          height: '100%',
                          background: theme.neutralGradient,
                          transition: 'width 0.3s ease'
                        }}></div>
                      </div>
                    </div>
                  </div>
                  <div style={{
                    marginTop: '20px',
                    padding: '16px',
                    background: theme.bgTertiary,
                    borderRadius: '6px',
                    borderLeft: `3px solid ${theme.brandPrimary}`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '600', color: theme.textSecondary }}>Total Storage</div>
                      <div style={{ fontSize: '12px', color: theme.textTertiary, marginTop: '2px' }}>
                        {s3Stats.files.total || 0} files across all locations
                      </div>
                    </div>
                    <div style={{ fontSize: '28px', fontWeight: '700', color: theme.textPrimary }}>
                      {Number(s3Stats.storage.total.gb || 0).toFixed(2)} <span style={{ fontSize: '16px', fontWeight: '500', color: theme.textSecondary }}>GB</span>
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
                  <div className="form-group" style={{ marginTop: '20px', padding: '16px', background: theme.bgTertiary, borderRadius: '6px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', margin: 0 }}>
                      <input
                        type="checkbox"
                        checked={s3Form.server_side_encryption}
                        onChange={(e) => setS3Form({...s3Form, server_side_encryption: e.target.checked})}
                        style={{ marginRight: '10px', width: '16px', height: '16px' }}
                      />
                      <span style={{ fontWeight: '500' }}>Enable Server-Side Encryption (AES-256)</span>
                    </label>
                    <div style={{ marginLeft: '26px', marginTop: '8px', fontSize: '13px', color: theme.textSecondary }}>
                      Encrypts files at rest in S3. Recommended for sensitive data.
                    </div>
                  </div>
                  <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: `1px solid ${theme.border}`, display: 'flex', gap: '12px' }}>
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
              <div className="card" style={{ background: theme.bgTertiary, border: `1px solid ${theme.border}` }}>
                <h3 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '600' }}>Integration Details</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', fontSize: '14px' }}>
                  <div>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', color: theme.textPrimary, marginBottom: '12px' }}>How It Works</h4>
                    <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8', color: theme.textSecondary }}>
                      <li>When enabled, new uploads are automatically stored in Amazon S3</li>
                      <li>Automatic fallback to local storage if S3 becomes unavailable</li>
                      <li>Existing files remain in their current storage location</li>
                      <li>Downloads are seamless regardless of storage location</li>
                    </ul>
                  </div>
                  <div>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', color: theme.textPrimary, marginBottom: '12px' }}>Required IAM Permissions</h4>
                    <div style={{ background: theme.bgCard, padding: '12px', borderRadius: '4px', border: `1px solid ${theme.border}` }}>
                      <code style={{ fontSize: '12px', color: theme.textPrimary, display: 'block', lineHeight: '1.6' }}>
                        s3:PutObject<br/>
                        s3:GetObject<br/>
                        s3:DeleteObject
                      </code>
                    </div>
                  </div>
                </div>
                <div style={{ marginTop: '20px', padding: '12px 16px', background: theme.infoLight, border: `1px solid ${theme.infoBg}`, borderRadius: '6px', fontSize: '13px', color: theme.info }}>
                  <strong>Security:</strong> All files are encrypted at rest with AES-256. Download URLs are time-limited and expire after 1 hour.
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ssl' && (
            <div className="admin-content">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div>
                  <h2 style={{ margin: 0 }}>SSL & HTTPS</h2>
                  <p style={{ margin: '4px 0 0 0', color: theme.textSecondary, fontSize: '14px' }}>
                  Manage certificate sources, Let's Encrypt automation, and HTTPS enforcement
                  </p>
                </div>
                {sslConfig && (
                  <span className={`status-badge ${sslConfig.enforce_https ? 'status-success' : 'status-info'}`} style={{ fontSize: '13px' }}>
                    {sslConfig.enforce_https ? 'HTTPS Enforced' : 'HTTPS Optional'}
                  </span>
                )}
              </div>

              {sslError && (
                <div style={{ marginBottom: '16px', padding: '12px 16px', borderRadius: '6px', background: theme.errorLight, border: `1px solid ${theme.errorBg}`, color: theme.error }}>
                  {sslError}
                </div>
              )}
              {sslMessage && (
                <div style={{ marginBottom: '16px', padding: '12px 16px', borderRadius: '6px', background: theme.successLight, border: `1px solid ${theme.successBg}`, color: theme.success }}>
                  {sslMessage}
                </div>
              )}

              {sslLoading ? (
                <p>Loading SSL configuration…</p>
              ) : (
                <>
                  <div className="card" style={{ marginBottom: '20px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '20px' }}>
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: '600', color: theme.textSecondary, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Certificate Source</div>
                        <div style={{ fontSize: '16px', fontWeight: '600', color: theme.textPrimary }}>{currentSslMode === 'uploaded' ? 'Uploaded Certificate' : 'Let\'s Encrypt'}</div>
                        <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                          {sslConfig?.primary_domain || 'No domain configured'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: '600', color: theme.textSecondary, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Certificate Status</div>
                        <div style={{ fontSize: '16px', fontWeight: '600', color: sslStatusLabel === 'verified' ? theme.success : theme.textPrimary }}>
                          {sslStatusLabel}
                        </div>
                        <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                          Expires {formatDateTime(sslConfig?.expires_at)}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: '600', color: theme.textSecondary, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Last Verified</div>
                        <div style={{ fontSize: '16px', fontWeight: '600', color: theme.textPrimary }}>
                          {formatDateTime(sslConfig?.last_verified_at)}
                        </div>
                        <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                          {sslConfig?.last_error ? `Last error: ${sslConfig.last_error}` : 'No recent errors'}
                        </div>
                      </div>
                    </div>
                    <div style={{ marginTop: '20px', display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                      {isLetsEncryptMode && (
                        <>
                          <button
                            className="btn btn-primary"
                            onClick={triggerIssuance}
                            disabled={sslProcessing || !sslSettingsForm.primary_domain}
                            type="button"
                          >
                            Request Certificate
                          </button>
                          <button
                            className="btn btn-secondary"
                            onClick={triggerRenewal}
                            disabled={sslProcessing || sslStatusLabel === 'pending_issue'}
                            type="button"
                          >
                            Force Renewal
                          </button>
                        </>
                      )}
                      <button
                        className={`btn ${sslConfig?.enforce_https ? 'btn-warning' : 'btn-success'}`}
                        onClick={() => toggleHttpsEnforcement(!sslConfig?.enforce_https)}
                        disabled={sslProcessing || !canEnforceHttps}
                        type="button"
                      >
                        {sslConfig?.enforce_https ? 'Disable HTTPS Enforcement' : 'Enable HTTPS Enforcement'}
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={triggerSslHealthCheck}
                        disabled={sslProcessing}
                        type="button"
                      >
                        Run Health Check
                      </button>
                    </div>
                  </div>

                  <div className="card" style={{ marginBottom: '20px' }}>
                    <h3 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '600' }}>Certificate Settings</h3>
                    <form onSubmit={submitSslSettings}>
                      <div style={{ display: 'flex', gap: '20px', marginBottom: '16px' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '500' }}>
                          <input
                            type="radio"
                            name="ssl-mode"
                            value="lets_encrypt"
                            checked={sslSettingsForm.mode === 'lets_encrypt'}
                            onChange={() => handleSslSettingsChange('mode', 'lets_encrypt')}
                          />
                          Let's Encrypt
                        </label>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '500' }}>
                          <input
                            type="radio"
                            name="ssl-mode"
                            value="uploaded"
                            checked={sslSettingsForm.mode === 'uploaded'}
                            onChange={() => handleSslSettingsChange('mode', 'uploaded')}
                          />
                          Uploaded Certificate
                        </label>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '500' }}>
                          <input
                            type="checkbox"
                            checked={sslSettingsForm.auto_renew}
                            onChange={(e) => handleSslSettingsChange('auto_renew', e.target.checked)}
                            disabled={!isLetsEncryptMode}
                          />
                          Auto renew (Let's Encrypt)
                        </label>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <div className="form-group">
                          <label style={{ fontWeight: '500', marginBottom: '6px', display: 'block' }}>Primary Domain</label>
                          <input
                            type="text"
                            placeholder="example.com"
                            value={sslSettingsForm.primary_domain}
                            onChange={(e) => handleSslSettingsChange('primary_domain', e.target.value)}
                            disabled={sslProcessing}
                            style={{ width: '100%' }}
                          />
                        </div>
                        <div className="form-group">
                          <label style={{ fontWeight: '500', marginBottom: '6px', display: 'block' }}>Alternate Domains (comma separated)</label>
                          <input
                            type="text"
                            placeholder="www.example.com, api.example.com"
                            value={sslSettingsForm.alternate_domains}
                            onChange={(e) => handleSslSettingsChange('alternate_domains', e.target.value)}
                            disabled={sslProcessing}
                            style={{ width: '100%' }}
                          />
                        </div>
                        <div className="form-group">
                          <label style={{ fontWeight: '500', marginBottom: '6px', display: 'block' }}>Verification Host Override</label>
                          <input
                            type="text"
                            placeholder="health.example.com"
                            value={sslSettingsForm.verification_hostname}
                            onChange={(e) => handleSslSettingsChange('verification_hostname', e.target.value)}
                            disabled={sslProcessing}
                            style={{ width: '100%' }}
                          />
                          <small style={{ display: 'block', marginTop: '6px', color: theme.textSecondary }}>
                            Optional host used to verify HTTPS after updates
                          </small>
                        </div>
                      </div>

                      <div style={{ marginTop: '20px', display: 'flex', gap: '12px' }}>
                        <button type="submit" className="btn btn-primary" disabled={sslProcessing}>
                          {sslProcessing ? 'Saving...' : 'Save SSL Settings'}
                        </button>
                        <button type="button" className="btn btn-secondary" onClick={fetchSslConfig} disabled={sslProcessing}>
                          Refresh
                        </button>
                      </div>
                    </form>
                  </div>

                  {currentSslMode === 'uploaded' && (
                    <div className="card" style={{ marginBottom: '20px' }}>
                      <h3 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '600' }}>Upload Certificate Files</h3>
                      <p style={{ marginBottom: '16px', color: theme.textSecondary, fontSize: '14px' }}>
                        Provide PEM-encoded files. The certificate should include the full chain (server + intermediates). The private key must be unencrypted.
                      </p>
                      <form onSubmit={submitSslUpload}>
                        <div className="form-group" style={{ marginBottom: '16px' }}>
                          <label style={{ fontWeight: '500', marginBottom: '6px', display: 'block' }}>Full Chain Certificate (.pem, .crt)</label>
                          <input
                            type="file"
                            accept=".pem,.crt,.cer,.txt"
                            onChange={(e) => handleSslFileChange('certificate_file', e.target.files)}
                            required
                          />
                          {sslUploadForm.certificate_file && (
                            <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                              Selected: {sslUploadForm.certificate_file.name}
                            </div>
                          )}
                        </div>
                        <div className="form-group" style={{ marginBottom: '16px' }}>
                          <label style={{ fontWeight: '500', marginBottom: '6px', display: 'block' }}>Private Key (.key, .pem)</label>
                          <input
                            type="file"
                            accept=".key,.pem,.txt"
                            onChange={(e) => handleSslFileChange('private_key_file', e.target.files)}
                            required
                          />
                          {sslUploadForm.private_key_file && (
                            <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                              Selected: {sslUploadForm.private_key_file.name}
                            </div>
                          )}
                        </div>
                        <div style={{ marginTop: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
                          <button type="submit" className="btn btn-primary" disabled={sslProcessing}>
                            {sslProcessing ? 'Uploading…' : 'Upload Certificate'}
                          </button>
                          <button
                            type="button"
                            className="btn btn-link"
                            onClick={() => setSslUploadForm({ certificate_file: null, private_key_file: null })}
                            disabled={sslProcessing}
                          >
                            Clear selection
                          </button>
                          {sslConfig?.uploaded?.uploaded_at && (
                            <span style={{ fontSize: '13px', color: theme.textSecondary }}>
                              Last upload: {formatDateTime(sslConfig.uploaded.uploaded_at)}
                            </span>
                          )}
                        </div>
                      </form>
                    </div>
                  )}

                  <div className="card" style={{ background: theme.bgTertiary, border: `1px solid ${theme.border}` }}>
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>Operational Notes</h3>
                    <ul style={{ margin: 0, paddingLeft: '20px', color: theme.textSecondary, lineHeight: '1.8', fontSize: '13px' }}>
                      <li>Let's Encrypt requires ports 80 and 443 to be reachable and DNS A records pointing to this server.</li>
                      <li>Uploaded certificates should be renewed manually before expiry. The platform will warn when expiry is near.</li>
                      <li>Enforcement redirects all HTTP requests to HTTPS and enables HSTS headers.</li>
                      <li>Health checks validate that HTTPS is working; failures are logged in the backend audit trail.</li>
                    </ul>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
