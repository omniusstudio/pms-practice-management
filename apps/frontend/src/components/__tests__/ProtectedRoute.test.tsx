import React from "react";
import { screen } from "@testing-library/react";
import { render } from "../../../tests/test-utils";
import "@testing-library/jest-dom";
import { describe, beforeEach, it, expect, vi } from "vitest";

// Import MemoryRouter from actual react-router-dom to avoid mock conflicts
const { MemoryRouter } = (await vi.importActual("react-router-dom")) as any;
import { ProtectedRoute, useRoleCheck, RoleGuard } from "../ProtectedRoute";
import { mockAuthContext } from "../../../tests/test-utils";

const TestComponent = () => <div>Protected Content</div>;

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mockAuthContext to default values
    Object.assign(mockAuthContext, {
      user: {
        id: "test-user-id",
        name: "Test User",
        email: "test@example.com",
        roles: ["clinician"],
      },
      isAuthenticated: true,
      isLoading: false,
      error: null,
    });
  });

  describe("authentication checks", () => {
    it("shows loading state when auth is loading", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: false,
        isLoading: true,
        user: null,
        error: null,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      expect(screen.getByText("Verifying authentication...")).toBeInTheDocument();
    });

    it("redirects to login when not authenticated", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
      });

      render(
        <MemoryRouter initialEntries={["/dashboard"]}>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      // Should redirect to login
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    });

    it("renders protected content when authenticated without role requirements", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "user-123",
          email: "test@example.com",
          name: "Test User",
          roles: ["clinician"],
          provider: "auth0",
        },
        error: null,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  describe("role-based access control", () => {
    const mockUser = {
      id: "user-123",
      email: "test@example.com",
      name: "Test User",
      roles: ["clinician", "front_desk"],
      provider: "auth0",
    };

    beforeEach(() => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: mockUser,
        error: null,
      });
    });

    it("allows access when user has required role", () => {
      render(
        <MemoryRouter>
          <ProtectedRoute requiredRoles={["clinician"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("allows access when user has any of the required roles", () => {
      render(
        <MemoryRouter>
          <ProtectedRoute requiredRoles={["admin", "clinician"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("redirects to unauthorized when user lacks required roles", () => {
      render(
        <MemoryRouter initialEntries={["/admin"]}>
          <ProtectedRoute requiredRoles={["admin"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      // Should redirect to unauthorized page
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    });

    it("handles multiple required roles correctly", () => {
      render(
        <MemoryRouter>
          <ProtectedRoute requiredRoles={["admin", "biller", "front_desk"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      // User has front_desk role, so should be allowed
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("denies access when user has no matching roles", () => {
      render(
        <MemoryRouter initialEntries={["/billing"]}>
          <ProtectedRoute requiredRoles={["admin", "biller"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      // User doesn't have admin or biller role
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    });
  });

  describe("useRoleCheck hook", () => {
    const TestRoleComponent = ({ roles }: { roles: string[] }) => {
      const hasAccess = useRoleCheck(roles);
      return <div>{hasAccess ? "Has Access" : "No Access"}</div>;
    };

    it("returns true when user has required role", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "user-123",
          email: "test@example.com",
          name: "Test User",
          roles: ["admin"],
          provider: "auth0",
        },
        error: null,
      });

      render(<TestRoleComponent roles={["admin"]} />);
      expect(screen.getByText("Has Access")).toBeInTheDocument();
    });

    it("returns false when user lacks required role", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "user-123",
          email: "test@example.com",
          name: "Test User",
          roles: ["clinician"],
          provider: "auth0",
        },
        error: null,
      });

      render(<TestRoleComponent roles={["admin"]} />);
      expect(screen.getByText("No Access")).toBeInTheDocument();
    });

    it("returns false when user is not authenticated", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
      });

      render(<TestRoleComponent roles={["admin"]} />);
      expect(screen.getByText("No Access")).toBeInTheDocument();
    });
  });

  describe("RoleGuard component", () => {
    beforeEach(() => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "user-123",
          email: "test@example.com",
          name: "Test User",
          roles: ["clinician"],
          provider: "auth0",
        },
        error: null,
      });
    });

    it("renders children when user has required role", () => {
      render(
        <RoleGuard requiredRoles={["clinician"]}>
          <div>Clinician Content</div>
        </RoleGuard>,
      );

      expect(screen.getByText("Clinician Content")).toBeInTheDocument();
    });

    it("renders nothing when user lacks required role and no fallback", () => {
      render(
        <RoleGuard requiredRoles={["admin"]}>
          <div>Admin Content</div>
        </RoleGuard>,
      );

      expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
    });

    it("renders fallback when user lacks required role", () => {
      render(
        <RoleGuard requiredRoles={["admin"]} fallback={<div>Insufficient Permissions</div>}>
          <div>Admin Content</div>
        </RoleGuard>,
      );

      expect(screen.getByText("Insufficient Permissions")).toBeInTheDocument();
      expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
    });
  });

  describe("specific role scenarios", () => {
    it("allows admin users to access admin route", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "admin-user",
          email: "admin@example.com",
          name: "Admin User",
          roles: ["admin"],
          provider: "auth0",
        },
        error: null,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute requiredRoles={["admin"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("allows front_desk and clinician users to access appointments", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "front-desk-user",
          email: "frontdesk@example.com",
          name: "Front Desk User",
          roles: ["front_desk"],
          provider: "auth0",
        },
        error: null,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute requiredRoles={["clinician", "admin", "front_desk"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("allows biller and admin users to access billing", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "biller-user",
          email: "biller@example.com",
          name: "Billing User",
          roles: ["biller"],
          provider: "auth0",
        },
        error: null,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute requiredRoles={["admin", "biller"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("denies non-admin users access to admin-only routes", () => {
      Object.assign(mockAuthContext, {
        isAuthenticated: true,
        isLoading: false,
        user: {
          id: "clinician-user",
          email: "clinician@example.com",
          name: "Clinician User",
          roles: ["clinician"],
          provider: "auth0",
        },
        error: null,
      });

      render(
        <MemoryRouter initialEntries={["/admin"]}>
          <ProtectedRoute requiredRoles={["admin"]}>
            <TestComponent />
          </ProtectedRoute>
        </MemoryRouter>,
      );

      // Should redirect to unauthorized
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    });
  });
});
