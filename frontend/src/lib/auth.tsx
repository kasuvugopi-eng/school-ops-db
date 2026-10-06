'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, TokenResponse } from '@/types';
import { api } from './api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, schoolName?: string) => Promise<void>;
  register: (data: {
    school_name: string;
    school_code: string;
    admin_email: string;
    admin_password: string;
    admin_full_name: string;
    admin_phone?: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const userData = await api.get<User>('/api/auth/me');
      setUser(userData);
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email: string, password: string, schoolName?: string) => {
    // Use form data format for OAuth2PasswordRequestForm compatibility
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    let url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/login`;
    if (schoolName && schoolName.trim()) {
      url += `?school_name=${encodeURIComponent(schoolName.trim())}`;
    }
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }
    
    const data: TokenResponse = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    setUser(data.user);
  };

  const register = async (data: {
    school_name: string;
    school_code: string;
    admin_email: string;
    admin_password: string;
    admin_full_name: string;
    admin_phone?: string;
  }) => {
    const response = await api.post<TokenResponse>('/api/auth/register', data);
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    setUser(response.user);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
