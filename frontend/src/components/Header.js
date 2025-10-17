import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';
import './Header.css';

const Header = ({
  currentPage = 'upload',
  showStorageInfo = false,
  showUserInfo = true,
  customActions = null,
  customTitle = null,
  customSubtitle = null
}) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const isAdmin = () => user?.role === 'admin';

  const getPageTitle = () => {
    if (customTitle) return customTitle;

    switch (currentPage) {
      case 'upload':
        return 'NGL - Next Gen LULA';
      case 'history':
        return 'Analysis History';
      case 'admin':
        return 'Admin Dashboard';
      case 'change-password':
        return 'Change Password';
      case 'results':
        return 'Analysis Results';
      default:
        return 'NGL - Next Gen LULA';
    }
  };

  const getPageSubtitle = () => {
    if (customSubtitle !== null) return customSubtitle;
    if (currentPage === 'upload') {
      return 'Next Generation LiveU Log Analyzer';
    }
    return null;
  };

  return (
    <header className="header">
      <div className="header-content">
        <img
          src="https://cdn-liveutv.pressidium.com/wp-content/uploads/2024/01/Live-and-Ulimted-Light-Background-V2.png"
          alt="LiveU Logo"
          className="header-logo"
        />
        <div className="header-text">
          <h1>{getPageTitle()}</h1>
          {getPageSubtitle() && <p>{getPageSubtitle()}</p>}
        </div>
      </div>

      <div className="header-actions">
        {showUserInfo && (
          <div className="user-info">
            <span className="username">{user?.username}</span>
            {isAdmin() && <span className="admin-badge">Admin</span>}
            {showStorageInfo && (
              <span className="storage-info">
                {user?.storage_used_mb?.toFixed(1) || 0} / {user?.storage_quota_mb || 0} MB
              </span>
            )}
          </div>
        )}

        <ThemeToggle />

        {/* Custom actions (for special pages like results view) */}
        {customActions ? (
          customActions
        ) : (
          <>
            {/* Navigation buttons - show different buttons based on current page */}
            {currentPage !== 'history' && (
              <button onClick={() => navigate('/history')} className="btn btn-secondary">
                History
              </button>
            )}

            {currentPage !== 'admin' && isAdmin() && (
              <button onClick={() => navigate('/admin')} className="btn btn-secondary">
                Admin
              </button>
            )}

            {currentPage !== 'upload' && (
              <button onClick={() => navigate('/')} className="btn btn-secondary">
                Upload
              </button>
            )}

            {currentPage !== 'change-password' && (
              <button onClick={() => navigate('/change-password')} className="btn btn-secondary">
                Change Password
              </button>
            )}

            <button onClick={logout} className="btn btn-secondary">
              Logout
            </button>
          </>
        )}
      </div>
    </header>
  );
};

export default Header;
