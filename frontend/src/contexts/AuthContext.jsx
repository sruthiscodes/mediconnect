import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI, setAuthToken, removeAuthToken, getAuthToken } from '../services/api';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const navigate = useNavigate();

  // Check if user is logged in on app start
  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = getAuthToken();
        const savedUser = localStorage.getItem('mediconnect_user');
        
        if (token && savedUser) {
          const userData = JSON.parse(savedUser);
          setUser(userData);
          setIsAuthenticated(true);
          
          // Verify token is still valid
          try {
            await authAPI.getCurrentUser();
            console.log('Token verified successfully');
          } catch (error) {
            console.log('Token verification failed:', error.message);
            // Token is invalid, clear auth state
            logout();
          }
        } else {
          console.log('No token or saved user found');
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        logout();
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    try {
      setLoading(true);
      const response = await authAPI.login(email, password);
      
      const { access_token, user: userData } = response;
      
      // Store auth data
      setAuthToken(access_token);
      localStorage.setItem('mediconnect_user', JSON.stringify(userData));
      
      // Update state
      setUser(userData);
      setIsAuthenticated(true);
      
      toast.success('Login successful!');
      
      // Navigate to dashboard
      navigate('/dashboard');
      
      return { success: true };
      
    } catch (error) {
      toast.error(error.message);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  const signup = async (email, password) => {
    try {
      setLoading(true);
      const response = await authAPI.signup(email, password);
      
      const { access_token, user: userData } = response;
      
      // Store auth data
      setAuthToken(access_token);
      localStorage.setItem('mediconnect_user', JSON.stringify(userData));
      
      // Update state
      setUser(userData);
      setIsAuthenticated(true);
      
      toast.success('Account created successfully!');
      
      // Navigate to dashboard
      navigate('/dashboard');
      
      return { success: true };
      
    } catch (error) {
      toast.error(error.message);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    removeAuthToken();
    localStorage.removeItem('mediconnect_user');
    setUser(null);
    setIsAuthenticated(false);
    toast.success('Logged out successfully');
    
    // Navigate to login page
    navigate('/login');
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    signup,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 