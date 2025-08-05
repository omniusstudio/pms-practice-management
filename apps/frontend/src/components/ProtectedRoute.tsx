import React, { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Logger } from "../utils/logger";

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoles?: string[];
  fallbackPath?: string;
}

/**
 * ProtectedRoute component that guards routes requiring authentication.
 * Redirects to login if user is not authenticated or lacks required roles.
 */
export function ProtectedRoute({
  children,
  requiredRoles = [],
  fallbackPath = "/login",
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Verifying authentication...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    Logger.info("Unauthorized access attempt", {
      component: "ProtectedRoute",
      action: "access_denied",
      path: location.pathname,
      reason: "not_authenticated",
    });

    return <Navigate to={fallbackPath} state={{ from: location.pathname }} replace />;
  }

  // Check role-based access if required roles are specified
  if (requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some((role) => user.roles.includes(role));

    if (!hasRequiredRole) {
      Logger.info("Insufficient permissions", {
        component: "ProtectedRoute",
        action: "access_denied",
        path: location.pathname,
        reason: "insufficient_roles",
        userRoles: user.roles,
        requiredRoles,
        userId: user.id,
      });

      return (
        <Navigate
          to="/unauthorized"
          state={{
            from: location.pathname,
            requiredRoles,
            userRoles: user.roles,
          }}
          replace
        />
      );
    }
  }

  // Log successful access for audit trail
  Logger.auditAction("page_access", location.pathname, user.id, {
    component: "ProtectedRoute",
    userRoles: user.roles,
    requiredRoles,
  });

  // Render protected content
  return <>{children}</>;
}

/**
 * Higher-order component version of ProtectedRoute
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  requiredRoles?: string[]
) {
  return function AuthenticatedComponent(props: P) {
    return (
      <ProtectedRoute requiredRoles={requiredRoles}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}

/**
 * Hook to check if user has specific roles
 */
export function useRoleCheck(requiredRoles: string[]): boolean {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || !user) {
    return false;
  }

  return requiredRoles.some((role) => user.roles.includes(role));
}

/**
 * Component to conditionally render content based on user roles
 */
interface RoleGuardProps {
  children: ReactNode;
  requiredRoles: string[];
  fallback?: ReactNode;
}

export function RoleGuard({ children, requiredRoles, fallback = null }: RoleGuardProps) {
  const hasAccess = useRoleCheck(requiredRoles);

  return hasAccess ? <>{children}</> : <>{fallback}</>;
}
