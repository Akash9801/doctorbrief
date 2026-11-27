import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi, getStoredToken, setStoredToken, setUnauthorizedHandler } from "@/services/api";
import type { Doctor } from "@/types/api";

interface AuthContextValue {
  doctor: Doctor | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    full_name: string;
    email: string;
    password: string;
    specialty?: string;
    clinic_name?: string;
    phone?: string;
    registration_number?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  setDoctor: React.Dispatch<React.SetStateAction<Doctor | null>>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    setStoredToken(null);
    setDoctor(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout();
    });
  }, [logout]);

  const refreshProfile = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setDoctor(null);
      setIsLoading(false);
      return;
    }
    try {
      const profile = await authApi.me();
      setDoctor(profile);
    } catch {
      setStoredToken(null);
      setDoctor(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login({ email, password });
    setStoredToken(res.access_token);
    setDoctor(res.doctor);
  }, []);

  const register = useCallback(
    async (payload: {
      full_name: string;
      email: string;
      password: string;
      specialty?: string;
      clinic_name?: string;
      phone?: string;
      registration_number?: string;
    }) => {
      const res = await authApi.register(payload);
      setStoredToken(res.access_token);
      setDoctor(res.doctor);
    },
    []
  );

  return (
    <AuthContext.Provider
      value={{
        doctor,
        isLoading,
        isAuthenticated: Boolean(doctor),
        login,
        register,
        logout,
        refreshProfile,
        setDoctor,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
