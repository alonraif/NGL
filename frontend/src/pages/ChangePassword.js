import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import '../App.css';

const ChangePassword = () => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { changePassword } = useAuth();
  const navigate = useNavigate();

  const validatePassword = (pwd) => {
    if (pwd.length < 12) {
      return 'Password must be at least 12 characters long';
    }
    if (!/[A-Z]/.test(pwd)) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(pwd)) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!/[0-9]/.test(pwd)) {
      return 'Password must contain at least one number';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validation
    if (!currentPassword) {
      setError('Current password is required');
      return;
    }

    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (currentPassword === newPassword) {
      setError('New password must be different from current password');
      return;
    }

    setLoading(true);

    try {
      const result = await changePassword(currentPassword, newPassword);

      if (result.success) {
        setSuccess('Password changed successfully! Redirecting...');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');

        // Redirect after 2 seconds
        setTimeout(() => {
          navigate('/');
        }, 2000);
      } else {
        setError(result.error || 'Failed to change password');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to change password. Please check your current password.');
    }

    setLoading(false);
  };

  const handleCancel = () => {
    navigate('/');
  };

  return (
    <div className="App">
      <div className="container">
        <Header currentPage="change-password" showStorageInfo={false} />

        <div className="card">
          <h2>Change Password</h2>

          <form onSubmit={handleSubmit}>
            {error && (
              <div className="error-message" style={{
                padding: '12px',
                marginBottom: '20px',
                background: 'var(--error-bg)',
                border: '1px solid var(--error)',
                borderRadius: '8px',
                color: 'var(--error)',
                textAlign: 'center'
              }}>
                {error}
              </div>
            )}

            {success && (
              <div className="success-message" style={{
                padding: '12px',
                marginBottom: '20px',
                background: 'var(--success-bg)',
                border: '1px solid var(--success)',
                borderRadius: '8px',
                color: 'var(--success)',
                textAlign: 'center'
              }}>
                {success}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="currentPassword">Current Password</label>
              <input
                type="password"
                id="currentPassword"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoFocus
                disabled={loading}
                className="input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="newPassword">New Password</label>
              <input
                type="password"
                id="newPassword"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                disabled={loading}
                className="input"
              />
              <small style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px', display: 'block' }}>
                Must be 12+ characters with uppercase, lowercase, and number
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm New Password</label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                className="input"
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
                style={{ flex: 1 }}
              >
                {loading ? 'Changing Password...' : 'Change Password'}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="btn btn-secondary"
                disabled={loading}
                style={{ flex: 1 }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChangePassword;
