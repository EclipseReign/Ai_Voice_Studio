import React, { createContext, useContext, useState, useEffect } from 'react';
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
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState(null);

  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  // Check existing session on mount
  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
      await fetchSubscription();
    } catch (error) {
      console.log('No existing session');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscription = async () => {
    try {
      const response = await axios.get(`${API}/subscription/status`, {
        withCredentials: true
      });
      setSubscription(response.data);
    } catch (error) {
      console.error('Error fetching subscription:', error);
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, {
        withCredentials: true
      });
      setUser(null);
      setSubscription(null);
    } catch (error) {
      console.error('Error during logout:', error);
    }
  };

  const refreshSubscription = async () => {
    await fetchSubscription();
  };

  const value = {
    user,
    loading,
    subscription,
    checkExistingSession,
    logout,
    refreshSubscription,
    isAuthenticated: !!user,
    isAdmin: user?.is_admin || false
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
