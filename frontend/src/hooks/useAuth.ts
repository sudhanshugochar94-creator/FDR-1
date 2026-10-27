import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { User, UserRole } from '@/types';

interface LoginResponse {
  access_token: string;
  user: User;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'fdr_token';
const USER_KEY = 'fdr_user';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem(USER_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        localStorage.removeItem(USER_KEY);
      }
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const navigate = useNavigate();

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (storedToken) {
        try {
          const res = await apiClient.get<User>('/api/auth/me');
          setUser(res.data);
          localStorage.setItem(USER_KEY, JSON.stringify(res.data));
        } catch (err) {
          console.warn('Could not verify current user session with server', err);
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    void initAuth();
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      try {
        const response = await apiClient.post<LoginResponse>('/api/auth/login', {
          email,
          password,
        });
        const authToken = response.data.access_token;
        const authUser = response.data.user;

        setToken(authToken);
        setUser(authUser);
        localStorage.setItem(TOKEN_KEY, authToken);
        localStorage.setItem(USER_KEY, JSON.stringify(authUser));

        navigate('/dashboard', { replace: true });
      } finally {
        setIsLoading(false);
      }
    },
    [navigate]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  const hasRole = useCallback(
    (roles: UserRole | UserRole[]) => {
      if (!user) return false;
      if (Array.isArray(roles)) {
        return roles.includes(user.role);
      }
      return user.role === roles;
    },
    [user]
  );

  return React.createElement(
    AuthContext.Provider,
    {
      value: {
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        hasRole,
      },
    },
    children
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default useAuth;
