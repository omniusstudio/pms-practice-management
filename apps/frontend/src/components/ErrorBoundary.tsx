import { Component, ErrorInfo, ReactNode } from "react";
import { Logger } from "../utils/logger";
import { scrubPHI } from "../utils/phi-scrubber";
import { captureSentryException, addSentryBreadcrumb } from "../services/sentryService";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

/**
 * Error Boundary component that catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of the component tree that crashed.
 * Ensures no PHI is exposed in error messages.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error with PHI scrubbing
    const scrubbedErrorInfo = {
      componentStack: scrubPHI(errorInfo.componentStack),
    };

    // Add breadcrumb for error context
    addSentryBreadcrumb("React Error Boundary caught an error", "error", "error", {
      component: "ErrorBoundary",
      url: window.location.href,
      userAgent: navigator.userAgent,
    });

    // Capture exception in Sentry
    captureSentryException(error, {
      errorInfo: scrubbedErrorInfo,
      component: "ErrorBoundary",
      url: window.location.href,
      userAgent: navigator.userAgent,
    });

    Logger.error("React Error Boundary caught an error", error, {
      component: "ErrorBoundary",
      action: "error_caught",
      errorInfo: scrubbedErrorInfo,
      url: window.location.href,
      userAgent: navigator.userAgent,
    });

    // Update state with error info
    this.setState({
      error,
      errorInfo,
    });
  }

  private handleRetry = () => {
    addSentryBreadcrumb("Error boundary retry attempted", "user", "info", {
      component: "ErrorBoundary",
    });

    Logger.info("Error boundary retry attempted", {
      component: "ErrorBoundary",
      action: "retry",
    });

    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  private handleReload = () => {
    addSentryBreadcrumb("Error boundary page reload initiated", "user", "info", {
      component: "ErrorBoundary",
    });

    Logger.info("Error boundary page reload initiated", {
      component: "ErrorBoundary",
      action: "reload",
    });

    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
              <svg
                className="h-6 w-6 text-red-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>

            <h2 className="text-lg font-semibold text-gray-900 mb-2">Something went wrong</h2>

            <p className="text-sm text-gray-600 mb-6">
              We encountered an unexpected error. Our team has been notified and is working to fix
              the issue.
            </p>

            <div className="space-y-3">
              <button
                onClick={this.handleRetry}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
              >
                Try Again
              </button>

              <button
                onClick={this.handleReload}
                className="w-full bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
              >
                Reload Page
              </button>
            </div>

            {process.env.NODE_ENV === "development" && this.state.error && (
              <details className="mt-6 text-left">
                <summary className="text-sm font-medium text-gray-700 cursor-pointer hover:text-gray-900">
                  Error Details (Development Only)
                </summary>
                <div className="mt-2 p-3 bg-gray-100 rounded text-xs font-mono text-gray-800 overflow-auto max-h-32">
                  <div className="mb-2">
                    <strong>Error:</strong> {scrubPHI(this.state.error.message)}
                  </div>
                  {this.state.error.stack && (
                    <div>
                      <strong>Stack:</strong>
                      <pre className="whitespace-pre-wrap mt-1">
                        {scrubPHI(this.state.error.stack)}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook version of Error Boundary for functional components
 */
export function useErrorHandler() {
  return (error: Error, errorInfo?: ErrorInfo) => {
    Logger.error("Unhandled error in component", error, {
      component: "useErrorHandler",
      action: "error_handled",
      errorInfo: errorInfo ? { componentStack: scrubPHI(errorInfo.componentStack) } : undefined,
      url: window.location.href,
    });
  };
}

/**
 * Simple error fallback component
 */
export function ErrorFallback({
  error: _error,
  resetError,
}: {
  error: Error;
  resetError: () => void;
}) {
  return (
    <div className="p-6 bg-red-50 border border-red-200 rounded-md">
      <div className="flex items-center">
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
          <h3 className="text-sm font-medium text-red-800">Error occurred</h3>
          <div className="mt-2 text-sm text-red-700">
            <p>Something went wrong. Please try again.</p>
          </div>
          <div className="mt-4">
            <button
              onClick={resetError}
              className="bg-red-100 px-3 py-2 rounded-md text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
