import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { Layout } from "../components/layout/Layout";
import { ErrorBoundary } from "../components/ErrorBoundary";

// Lazy load pages for better performance
const LoginPage = React.lazy(() => import("../pages/LoginPage"));
const DashboardPage = React.lazy(() => import("../pages/DashboardPage"));
const AccessReviewPage = React.lazy(() => import("../pages/AccessReviewPage"));
const UnauthorizedPage = React.lazy(() => import("../pages/UnauthorizedPage"));
const NotFoundPage = React.lazy(() => import("../pages/NotFoundPage"));

// Loading component for lazy-loaded routes
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p className="mt-4 text-gray-600">Loading...</p>
    </div>
  </div>
);

// Wrapper component for lazy-loaded pages with error boundary
const LazyPageWrapper = ({ children }: { children: React.ReactNode }) => (
  <ErrorBoundary>
    <React.Suspense fallback={<PageLoader />}>{children}</React.Suspense>
  </ErrorBoundary>
);

// Router configuration
export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/login",
    element: (
      <LazyPageWrapper>
        <LoginPage />
      </LazyPageWrapper>
    ),
  },
  {
    path: "/unauthorized",
    element: (
      <LazyPageWrapper>
        <UnauthorizedPage />
      </LazyPageWrapper>
    ),
  },
  {
    path: "/dashboard",
    element: (
      <ProtectedRoute>
        <Layout>
          <LazyPageWrapper>
            <DashboardPage />
          </LazyPageWrapper>
        </Layout>
      </ProtectedRoute>
    ),
  },
  // Protected routes for different user roles
  {
    path: "/patients",
    element: (
      <ProtectedRoute requiredRoles={["clinician", "admin"]}>
        <Layout>
          <LazyPageWrapper>
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900">Patient Management</h1>
              <p className="mt-2 text-gray-600">Manage patient records and appointments.</p>
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-blue-800">🚧 Patient management features coming soon...</p>
              </div>
            </div>
          </LazyPageWrapper>
        </Layout>
      </ProtectedRoute>
    ),
  },
  {
    path: "/appointments",
    element: (
      <ProtectedRoute requiredRoles={["clinician", "admin", "staff"]}>
        <Layout>
          <LazyPageWrapper>
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900">Appointments</h1>
              <p className="mt-2 text-gray-600">Schedule and manage appointments.</p>
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-blue-800">🚧 Appointment scheduling features coming soon...</p>
              </div>
            </div>
          </LazyPageWrapper>
        </Layout>
      </ProtectedRoute>
    ),
  },
  {
    path: "/billing",
    element: (
      <ProtectedRoute requiredRoles={["admin", "billing"]}>
        <Layout>
          <LazyPageWrapper>
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900">Billing & Insurance</h1>
              <p className="mt-2 text-gray-600">Manage billing and insurance claims.</p>
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-blue-800">🚧 Billing features coming soon...</p>
              </div>
            </div>
          </LazyPageWrapper>
        </Layout>
      </ProtectedRoute>
    ),
  },
  {
    path: "/reports",
    element: (
      <ProtectedRoute requiredRoles={["admin"]}>
        <Layout>
          <LazyPageWrapper>
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
              <p className="mt-2 text-gray-600">View practice analytics and reports.</p>
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-blue-800">🚧 Reporting features coming soon...</p>
              </div>
            </div>
          </LazyPageWrapper>
        </Layout>
      </ProtectedRoute>
    ),
  },
  {
    path: "/access-review",
    element: (
      <ProtectedRoute requiredRoles={["admin"]}>
        <Layout>
          <LazyPageWrapper>
            <AccessReviewPage />
          </LazyPageWrapper>
        </Layout>
      </ProtectedRoute>
    ),
  },
  {
    path: "/settings",
    element: (
      <ProtectedRoute requiredRoles={["admin"]}>
        <Layout>
          <LazyPageWrapper>
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
              <p className="mt-2 text-gray-600">Configure system settings and user management.</p>
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-blue-800">🚧 Settings features coming soon...</p>
              </div>
            </div>
          </LazyPageWrapper>
        </Layout>
      </ProtectedRoute>
    ),
  },
  // Catch-all route for 404 errors
  {
    path: "*",
    element: (
      <LazyPageWrapper>
        <NotFoundPage />
      </LazyPageWrapper>
    ),
  },
]);

// Route definitions for navigation
export const routes = {
  home: "/",
  login: "/login",
  dashboard: "/dashboard",
  patients: "/patients",
  appointments: "/appointments",
  billing: "/billing",
  reports: "/reports",
  accessReview: "/access-review",
  settings: "/settings",
  unauthorized: "/unauthorized",
} as const;

// Navigation items with role requirements
export const navigationItems = [
  {
    name: "Dashboard",
    href: routes.dashboard,
    icon: "HomeIcon",
    requiredRoles: [],
  },
  {
    name: "Patients",
    href: routes.patients,
    icon: "UsersIcon",
    requiredRoles: ["clinician", "admin"],
  },
  {
    name: "Appointments",
    href: routes.appointments,
    icon: "CalendarIcon",
    requiredRoles: ["clinician", "admin", "staff"],
  },
  {
    name: "Billing",
    href: routes.billing,
    icon: "CreditCardIcon",
    requiredRoles: ["admin", "billing"],
  },
  {
    name: "Reports",
    href: routes.reports,
    icon: "ChartBarIcon",
    requiredRoles: ["admin"],
  },
  {
    name: "Access Review",
    href: routes.accessReview,
    icon: "ShieldCheckIcon",
    requiredRoles: ["admin"],
  },
  {
    name: "Settings",
    href: routes.settings,
    icon: "CogIcon",
    requiredRoles: ["admin"],
  },
] as const;
