import { createContext, useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import authService from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const decodeToken = (token) => {
  try {
    if (!token || typeof token !== 'string') {
      return null;
    }
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }
    const decoded = JSON.parse(atob(parts[1]));
    return decoded;
  } catch (error) {
    console.error('Token decode error:', error);
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (token) {
      const decoded = decodeToken(token);
      // Drop expired tokens on load/refresh so protected routes re-prompt login.
      if (decoded) {
        const now = Math.floor(Date.now() / 1000);
        if (decoded.exp && decoded.exp < now) {
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        } else {
          setUser(decoded);
        }
      } else {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
      }
    }
  }, [token]);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const data = await authService.login({ email, password });
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        const decoded = decodeToken(data.access_token);
        if (decoded) {
          setUser(decoded);
        }
        toast.success('Login successful!');
        navigate('/dashboard');
      } else {
        throw new Error('No token in response');
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || 'Login failed';
      toast.error(errorMsg);
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  const register = async (name, email, password) => {
    setLoading(true);
    try {
      const data = await authService.register({ name, email, password });
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        const decoded = decodeToken(data.access_token);
        if (decoded) {
          setUser(decoded);
        }
        const message = data.message || 'Registration successful!';
        toast.success(message);
        navigate('/dashboard');
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || 'Registration failed';
      toast.error(errorMsg);
      console.error('Register error:', error);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    toast.info('Logged out successfully');
    navigate('/login');
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!token && !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};