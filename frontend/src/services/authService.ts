import { API_BASE } from "../config/api";
import { AuthUser, LoginResponse, UserRole } from "../types/user";

export type { AuthUser, LoginResponse, UserRole };

const TOKEN_KEY = "sd_owner_token";
const USER_KEY = "sd_owner_user";

export const authService = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },

  getUser(): AuthUser | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  isAuthenticated(): boolean {
    return !!this.getToken() && !!this.getUser();
  },

  setSession(data: LoginResponse): void {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    const user: AuthUser = {
      id: data.user_id,
      username: data.username,
      role: data.role,
      must_change_password: data.must_change_password
    };
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  clearSession(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  async login(username: string, password: string): Promise<LoginResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Authentication failed. Please verify credentials.");
    }

    const data: LoginResponse = await res.json();
    this.setSession(data);
    return data;
  },

  async getMe(): Promise<AuthUser> {
    const token = this.getToken();
    if (!token) throw new Error("Not authenticated");

    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
      this.clearSession();
      throw new Error("Session expired. Please log in again.");
    }

    const user: AuthUser = await res.json();
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const token = this.getToken();
    if (!token) throw new Error("Not authenticated");

    const res = await fetch(`${API_BASE}/auth/change-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to update password" }));
      throw new Error(err.detail || "Password change failed");
    }

    const user = this.getUser();
    if (user) {
      user.must_change_password = false;
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
  },

  async updateProfile(data: { username?: string; email?: string }): Promise<AuthUser> {
    const token = this.getToken();
    if (!token) throw new Error("Not authenticated");

    const res = await fetch(`${API_BASE}/auth/update-profile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to update profile" }));
      throw new Error(err.detail || "Profile update failed");
    }

    const updatedUser: AuthUser = await res.json();
    localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
    return updatedUser;
  },

  hasRole(allowedRoles: string[]): boolean {
    const user = this.getUser();
    if (!user) return false;
    const userRole = (user.role || "").toUpperCase();
    if (userRole === "MASTER" || userRole === "OWNER") return true;
    const normalized = allowedRoles.map(r => r.toUpperCase());
    return normalized.includes(userRole);
  }
};
