import React, { createContext, useContext, useReducer, useEffect, ReactNode } from "react";
import { authService, User } from "../services/authService";
import { Logger } from "../utils/logger";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

type AuthAction =
  | { type: "AUTH_START" }
  | { type: "AUTH_SUCCESS"; payload: User }
  | { type: "AUTH_ERROR"; payload: string }
  | { type: "AUTH_LOGOUT" }
  | { type: "CLEAR_ERROR" };

interface AuthContextType extends AuthState {
  login: () => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "AUTH_START":
      return {
        ...state,
        isLoading: true,
        error: null,
      };
    case "AUTH_SUCCESS":
      return {
        ...state,
        user: action.payload,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };
    case "AUTH_ERROR":
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload,
      };
    case "AUTH_LOGOUT":
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    case "CLEAR_ERROR":
      return {
        ...state,
        error: null,
      };
    default:
      return state;
  }
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const login = async () => {
    try {
      dispatch({ type: "AUTH_START" });
      await authService.login();
      // Login redirects to OIDC provider, so we don't handle success here
    } catch (error) {
      const message = error instanceof Error ? error.message : "Login failed";
      Logger.error("Login failed", error as Error, {
        component: "AuthProvider",
        action: "login",
      });
      dispatch({ type: "AUTH_ERROR", payload: message });
    }
  };

  const logout = async () => {
    try {
      dispatch({ type: "AUTH_START" });
      await authService.logout();
      const userId = state.user?.id || "unknown";
      dispatch({ type: "AUTH_LOGOUT" });
      Logger.auditAction("logout", "system", userId, {
        component: "AuthProvider",
        action: "logout",
        userId,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Logout failed";
      Logger.error("Logout failed", error as Error, {
        component: "AuthProvider",
        action: "logout_failed",
        userId: state.user?.id || "unknown",
      });
      dispatch({ type: "AUTH_ERROR", payload: message });
    }
  };

  const clearError = () => {
    dispatch({ type: "CLEAR_ERROR" });
  };

  // Check authentication status on mount and handle callback
  useEffect(() => {
    const checkAuth = async () => {
      try {
        dispatch({ type: "AUTH_START" });

        // Handle OIDC callback if present
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has("access_token")) {
          const token = urlParams.get("access_token");
          const userId = urlParams.get("user_id");

          if (token && userId) {
            // Store token and get user info
            authService.setToken(token);
            const user = await authService.getCurrentUser();
            dispatch({ type: "AUTH_SUCCESS", payload: user });

            // Clean up URL
            window.history.replaceState({}, document.title, window.location.pathname);
            return;
          }
        }

        // Check existing authentication
        const user = await authService.getCurrentUser();
        if (user) {
          dispatch({ type: "AUTH_SUCCESS", payload: user });
        } else {
          dispatch({ type: "AUTH_LOGOUT" });
        }
      } catch (error) {
        Logger.error("Auth check failed", error as Error, {
          component: "AuthProvider",
          action: "checkAuth",
        });
        dispatch({ type: "AUTH_LOGOUT" });
      }
    };

    checkAuth();
  }, []);

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
