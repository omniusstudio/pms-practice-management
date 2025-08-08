/**
 * Demo component showcasing feature flag usage
 * This component demonstrates various feature flag patterns
 */

import React from "react";
import {
  useFeatureFlag,
  useAllFeatureFlags,
  useKillSwitch,
  withFeatureFlag,
  clearFeatureFlagCache,
} from "../hooks/useFeatureFlags";

// Example component that's conditionally rendered based on feature flag
const AdvancedReportingComponent: React.FC = () => (
  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
    <h3 className="text-lg font-semibold text-blue-800 mb-2">Advanced Reporting</h3>
    <p className="text-blue-600">This advanced reporting feature is enabled via feature flags!</p>
  </div>
);

// Wrap component with feature flag HOC
const ConditionalAdvancedReporting = withFeatureFlag("advanced_reporting_enabled", false, () => (
  <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
    <p className="text-gray-600">Advanced reporting is currently disabled.</p>
  </div>
))(AdvancedReportingComponent);

const FeatureFlagDemo: React.FC = () => {
  // Individual feature flag hooks
  const {
    isEnabled: videoCallsEnabled,
    isLoading: videoCallsLoading,
    error: videoCallsError,
    refetch: refetchVideoCalls,
  } = useFeatureFlag("video_calls_enabled", false);

  const {
    isEnabled: paymentsEnabled,
    isLoading: paymentsLoading,
    error: paymentsError,
  } = useFeatureFlag("payments_enabled", false);

  // Kill switch hook
  const {
    isEnabled: ediEnabled,
    isLoading: ediLoading,
    error: ediError,
  } = useKillSwitch("edi-integration");

  // All flags hook
  const {
    flags,
    isLoading: allFlagsLoading,
    error: allFlagsError,
    refetch: refetchAllFlags,
  } = useAllFeatureFlags();

  const handleClearCache = () => {
    clearFeatureFlagCache();
    refetchVideoCalls();
    refetchAllFlags();
  };

  if (videoCallsLoading || paymentsLoading || ediLoading || allFlagsLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="bg-white shadow-lg rounded-lg p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Feature Flags Demo</h1>

        {/* Individual Feature Flags */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Video Calls</h3>
            <div className="flex items-center space-x-2">
              <span
                className={`px-2 py-1 rounded text-sm ${
                  videoCallsEnabled ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                }`}
              >
                {videoCallsEnabled ? "Enabled" : "Disabled"}
              </span>
              {videoCallsError && (
                <span className="text-red-500 text-sm">Error: {videoCallsError}</span>
              )}
            </div>
            {videoCallsEnabled && (
              <div className="mt-2 p-2 bg-green-50 rounded">
                <p className="text-sm text-green-700">🎥 Video calling feature is available!</p>
              </div>
            )}
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">Payments</h3>
            <div className="flex items-center space-x-2">
              <span
                className={`px-2 py-1 rounded text-sm ${
                  paymentsEnabled ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                }`}
              >
                {paymentsEnabled ? "Enabled" : "Disabled"}
              </span>
              {paymentsError && (
                <span className="text-red-500 text-sm">Error: {paymentsError}</span>
              )}
            </div>
            {paymentsEnabled && (
              <div className="mt-2 p-2 bg-green-50 rounded">
                <p className="text-sm text-green-700">💳 Payment processing is available!</p>
              </div>
            )}
          </div>
        </div>

        {/* Kill Switch Example */}
        <div className="p-4 border rounded-lg mb-6">
          <h3 className="font-semibold mb-2">EDI Integration (Kill Switch)</h3>
          <div className="flex items-center space-x-2">
            <span
              className={`px-2 py-1 rounded text-sm ${
                ediEnabled ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
              }`}
            >
              {ediEnabled ? "Active" : "Disabled"}
            </span>
            {ediError && <span className="text-red-500 text-sm">Error: {ediError}</span>}
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Kill switches allow immediate disabling of critical features.
          </p>
        </div>

        {/* HOC Example */}
        <div className="mb-6">
          <h3 className="font-semibold mb-2">HOC Pattern Example</h3>
          <ConditionalAdvancedReporting />
        </div>

        {/* All Flags Display */}
        <div className="p-4 border rounded-lg mb-6">
          <h3 className="font-semibold mb-2">All Feature Flags</h3>
          {allFlagsError ? (
            <p className="text-red-500">Error loading flags: {allFlagsError}</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {Object.entries(flags).map(([flagName, flagValue]) => (
                <div
                  key={flagName}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded"
                >
                  <span className="text-sm font-mono">{flagName}</span>
                  <span
                    className={`px-2 py-1 rounded text-xs ${
                      flagValue ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                    }`}
                  >
                    {flagValue ? "ON" : "OFF"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex space-x-4">
          <button
            onClick={handleClearCache}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          >
            Clear Cache & Refresh
          </button>
          <button
            onClick={refetchAllFlags}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
          >
            Refresh All Flags
          </button>
        </div>

        {/* Debug Info */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-semibold mb-2">Debug Information</h4>
          <div className="text-sm text-gray-600 space-y-1">
            <p>Environment: {process.env.NODE_ENV || "development"}</p>
            <p>Total Flags: {Object.keys(flags).length}</p>
            <p>Enabled Flags: {Object.values(flags).filter(Boolean).length}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FeatureFlagDemo;
