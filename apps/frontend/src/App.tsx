import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { router } from "./router";
import { initSentry } from "./services/sentryService";
import "./App.css";

function App() {
  useEffect(() => {
    // Initialize Sentry error tracking
    initSentry();
  }, []);

  return (
    <ErrorBoundary>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
