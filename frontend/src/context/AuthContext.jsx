import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../api/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('iev_user');
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch (e) {}
    }
    setLoading(false);
  }, []);

  const login = async ({ username, role, password }) => {
    const { data } = await api.post('/auth/login', { username, role, password });
    if (!data.success) throw new Error(data.message || 'Error al iniciar sesión');
    const u = { username: data.username, role: data.role, token: data.token };
    localStorage.setItem('iev_user', JSON.stringify(u));
    localStorage.setItem('iev_token', data.token);
    setUser(u);
    return u;
  };

  const register = async ({ username, email, password }) => {
    const { data } = await api.post('/auth/register', { username, email, password });
    return data;
  };

  const logout = () => {
    localStorage.removeItem('iev_user');
    localStorage.removeItem('iev_token');
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isAdmin, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
