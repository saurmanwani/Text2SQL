/* eslint-disable react-refresh/only-export-components */
import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

import { api, TOKEN_KEY, type User } from "@/lib/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  authenticate: (mode: "login" | "register", email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(TOKEN_KEY)));

  useEffect(() => {
    const expire = () => {
      setUser(null);
      setLoading(false);
    };
    window.addEventListener("auth:expired", expire);
    if (localStorage.getItem(TOKEN_KEY)) {
      api.me().then(setUser).catch(expire).finally(() => setLoading(false));
    }
    return () => window.removeEventListener("auth:expired", expire);
  }, []);

  const authenticate = async (
    mode: "login" | "register",
    email: string,
    password: string,
  ) => {
    const result = await api.auth(mode, email, password);
    localStorage.setItem(TOKEN_KEY, result.access_token);
    setUser(result.user);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, authenticate, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
