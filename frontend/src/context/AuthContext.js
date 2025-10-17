import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [lastActivity, setLastActivity] = useState(Date.now());

  // Configure axios defaults
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get('/api/auth/me');
      setUser(response.data);
      setLastActivity(Date.now());
    } catch (error) {
      console.error('Failed to fetch user:', error);
      // Token invalid, clear it
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password
      });

      if (response.data.success) {
        const { access_token, user } = response.data;
        setToken(access_token);
        setUser(user);
        setLastActivity(Date.now());
        localStorage.setItem('token', access_token);
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        return { success: true };
      }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Login failed'
      };
    }
  };

  const register = async (username, email, password) => {
    try {
      const response = await axios.post('/api/auth/register', {
        username,
        email,
        password
      });

      if (response.data.success) {
        // Auto-login after registration
        return await login(username, password);
      }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Registration failed'
      };
    }
  };

  const logout = useCallback(async () => {
    try {
      if (token) {
        await axios.post('/api/auth/logout');
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  const changePassword = async (currentPassword, newPassword) => {
    try {
      const response = await axios.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });

      return { success: response.data.success };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Password change failed'
      };
    }
  };

  const isAdmin = () => {
    return user && user.role === 'admin';
  };

  // Auto-logout after 10 minutes of inactivity
  useEffect(() => {
    if (!user || !token) return;

    const INACTIVITY_TIMEOUT = 10 * 60 * 1000; // 10 minutes in milliseconds

    // Activity event listeners
    const activityEvents = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click'
    ];

    const updateActivity = () => {
      const now = Date.now();
      const timeSinceLastActivity = now - lastActivity;

      if (timeSinceLastActivity >= INACTIVITY_TIMEOUT) {
        console.log('[AuthContext] User inactive for 10 minutes, logging out from activity event...');
        logout();
        return;
      }

      setLastActivity(now);
    };

    // Add event listeners
    activityEvents.forEach(event => {
      document.addEventListener(event, updateActivity);
    });

    // Check for inactivity every minute
    const inactivityChecker = setInterval(() => {
      const now = Date.now();
      const timeSinceLastActivity = now - lastActivity;

      if (timeSinceLastActivity >= INACTIVITY_TIMEOUT) {
        console.log('[AuthContext] User inactive for 10 minutes, logging out...');
        logout();
      }
    }, 60 * 1000); // Check every minute

    // Cleanup
    return () => {
      activityEvents.forEach(event => {
        document.removeEventListener(event, updateActivity);
      });
      clearInterval(inactivityChecker);
    };
  }, [user, token, lastActivity, logout]);

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    changePassword,
    isAdmin
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
