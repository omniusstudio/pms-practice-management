/**
 * Authentication service for OIDC integration with backend.
 * Handles login, logout, token management, and user data.
 */

import { api } from "../utils/http-client";
import { Logger } from "../utils/logger";
import { scrubPHI } from "../utils/phi-scrubber";

export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  provider: string;
  lastLogin?: string;
}

interface LoginResponse {
  authorization_url: string;
  state: string;
}

class AuthService {
  private readonly TOKEN_KEY = "pms_access_token";
  private readonly USER_KEY = "pms_user";
  private readonly API_BASE = "/auth";

  /**
   * Initiate OIDC login flow
   */
  async login(redirectUrl?: string): Promise<void> {
    try {
      const response = await api.post<LoginResponse>(`${this.API_BASE}/login`, {
        provider: "auth0", // Default provider
        redirect_url: redirectUrl || window.location.origin + "/dashboard",
      });

      Logger.info("Login initiated", {
        component: "AuthService",
        action: "login",
        state: response.state.substring(0, 8) + "...",
      });

      // Redirect to OIDC provider
      window.location.href = response.authorization_url;
    } catch (error) {
      Logger.error("Login initiation failed", error as Error, {
        component: "AuthService",
        action: "login",
      });
      throw new Error("Failed to initiate login. Please try again.");
    }
  }

  /**
   * Logout user and clear tokens
   */
  async logout(): Promise<void> {
    try {
      const token = this.getToken();
      if (token) {
        // Call backend logout endpoint
        await api.post(`${this.API_BASE}/logout`);
      }
    } catch (error) {
      Logger.error("Logout API call failed", error as Error, {
        component: "AuthService",
        action: "logout",
      });
      // Continue with local cleanup even if API call fails
    } finally {
      // Clear local storage
      this.clearTokens();

      Logger.info("User logged out locally", {
        component: "AuthService",
        action: "logout",
      });
    }
  }

  /**
   * Get current authenticated user
   */
  async getCurrentUser(): Promise<User | null> {
    try {
      const token = this.getToken();
      if (!token) {
        return null;
      }

      // Check if we have cached user data
      const cachedUser = this.getCachedUser();
      if (cachedUser && this.isTokenValid()) {
        return cachedUser;
      }

      // Fetch user from backend
      const user = await api.get<User>(`${this.API_BASE}/user`);

      // Cache user data
      this.setCachedUser(user);

      Logger.info("User data retrieved", {
        component: "AuthService",
        action: "getCurrentUser",
        userId: user.id,
      });

      return user;
    } catch (error) {
      Logger.error("Failed to get current user", error as Error, {
        component: "AuthService",
        action: "getCurrentUser",
      });

      // Clear invalid tokens
      this.clearTokens();
      return null;
    }
  }

  /**
   * Set authentication token
   */
  setToken(token: string): void {
    try {
      localStorage.setItem(this.TOKEN_KEY, token);

      // Set token expiry (default 30 minutes from now)
      const expiryTime = Date.now() + 30 * 60 * 1000;
      localStorage.setItem(`${this.TOKEN_KEY}_expiry`, expiryTime.toString());

      Logger.info("Token stored", {
        component: "AuthService",
        action: "setToken",
      });
    } catch (error) {
      Logger.error("Failed to store token", error as Error, {
        component: "AuthService",
        action: "setToken",
      });
      throw new Error("Failed to store authentication token");
    }
  }

  /**
   * Get authentication token
   */
  getToken(): string | null {
    try {
      const token = localStorage.getItem(this.TOKEN_KEY);
      if (!token || !this.isTokenValid()) {
        this.clearTokens();
        return null;
      }
      return token;
    } catch (error) {
      Logger.error("Failed to retrieve token", error as Error, {
        component: "AuthService",
        action: "getToken",
      });
      return null;
    }
  }

  /**
   * Check if current token is valid (not expired)
   */
  private isTokenValid(): boolean {
    try {
      const expiryTime = localStorage.getItem(`${this.TOKEN_KEY}_expiry`);
      if (!expiryTime) {
        return false;
      }

      return Date.now() < parseInt(expiryTime, 10);
    } catch (error) {
      return false;
    }
  }

  /**
   * Get cached user data
   */
  private getCachedUser(): User | null {
    try {
      const userData = localStorage.getItem(this.USER_KEY);
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      Logger.error("Failed to parse cached user data", error as Error, {
        component: "AuthService",
        action: "getCachedUser",
      });
      return null;
    }
  }

  /**
   * Cache user data
   */
  private setCachedUser(user: User): void {
    try {
      // Scrub any potential PHI before caching
      const safeUser = {
        ...user,
        email: scrubPHI(user.email),
        name: scrubPHI(user.name),
      };

      localStorage.setItem(this.USER_KEY, JSON.stringify(safeUser));
    } catch (error) {
      Logger.error("Failed to cache user data", error as Error, {
        component: "AuthService",
        action: "setCachedUser",
      });
    }
  }

  /**
   * Clear all authentication tokens and cached data
   */
  private clearTokens(): void {
    try {
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(`${this.TOKEN_KEY}_expiry`);
      localStorage.removeItem(this.USER_KEY);
    } catch (error) {
      Logger.error("Failed to clear tokens", error as Error, {
        component: "AuthService",
        action: "clearTokens",
      });
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Get authorization header for API requests
   */
  getAuthHeader(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}

// Export singleton instance
export const authService = new AuthService();

// Export hook for React components
export const useAuthService = () => authService;
