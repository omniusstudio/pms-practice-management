import React, { useState, useEffect } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Logger } from "../utils/logger";

const LoginPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user, login, isLoading: authLoading } = useAuth();
  const [searchParams] = useSearchParams();

  // If user is already authenticated, redirect to dashboard
  if (user && !authLoading) {
    const returnUrl = searchParams.get("returnUrl") || "/dashboard";
    return <Navigate to={returnUrl} replace />;
  }

  const handleLogin = async () => {
    setIsLoading(true);
    setError(null);

    try {
      Logger.info("Login attempt initiated", {
        component: "LoginPage",
        action: "login_attempt",
      });

      await login();

      Logger.auditAction("login_success", "authentication", "system", {
        component: "LoginPage",
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Login failed";
      setError(errorMessage);

      Logger.error("Login failed", err as Error, {
        component: "LoginPage",
        action: "login_failed",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle OIDC callback errors
  useEffect(() => {
    const errorParam = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (errorParam) {
      const errorMessage = errorDescription || `Authentication error: ${errorParam}`;
      setError(errorMessage);

      Logger.error("OIDC callback error", new Error(errorMessage), {
        component: "LoginPage",
        action: "oidc_callback_error",
        error: errorParam,
        errorDescription,
      });
    }
  }, [searchParams]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Checking authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-16 w-16 bg-indigo-600 rounded-full flex items-center justify-center">
            <span className="text-white font-bold text-xl">PMS</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Mental Health Practice Management System
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            HIPAA-compliant patient management platform
          </p>
        </div>

        <div className="mt-8 space-y-6">
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Authentication Error</h3>
                  <div className="mt-2 text-sm text-red-700">
                    <p>{error}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              onClick={handleLogin}
              disabled={isLoading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Signing in...
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  Sign in with SSO
                </>
              )}
            </button>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 space-y-1">
              <p>🔒 HIPAA Compliant • End-to-End Encrypted</p>
              <p>Secure authentication powered by OIDC</p>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-gray-200 pt-6">
          <div className="text-center text-xs text-gray-500">
            <p>For support, contact your system administrator</p>
            <p className="mt-1">© 2024 Mental Health PMS. All rights reserved.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
