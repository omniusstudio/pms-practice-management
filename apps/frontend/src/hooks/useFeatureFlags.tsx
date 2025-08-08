/**
 * React hook for feature flag management
 * Provides client-side feature flag evaluation with caching and error handling
 */

import { useState, useEffect, useCallback, useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";
import { httpClient } from "../utils/http-client";
import { logger } from "../utils/logger";

interface FeatureFlagContext {
  user_id?: string;
  ip_address?: string;
  environment?: string;
  [key: string]: any;
}

interface FlagEvaluationRequest {
  flag_name: string;
  context: FeatureFlagContext;
  default_value: boolean;
}

interface FlagEvaluationResponse {
  flag_name: string;
  flag_value: boolean;
  evaluation_context: FeatureFlagContext;
}

interface AllFlagsResponse {
  flags: Record<string, boolean>;
  environment: string;
}

interface FlagInfo {
  name: string;
  value: boolean;
  environment: string;
  last_updated: string;
}

interface UseFeatureFlagResult {
  isEnabled: boolean;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

interface UseAllFlagsResult {
  flags: Record<string, boolean>;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Cache for flag values to avoid repeated API calls
const flagCache = new Map<string, { value: boolean; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Hook to evaluate a single feature flag
 * @param flagName - Name of the feature flag
 * @param defaultValue - Default value if flag evaluation fails
 * @param context - Additional context for flag evaluation
 */
export const useFeatureFlag = (
  flagName: string,
  defaultValue: boolean = false,
  context: Partial<FeatureFlagContext> = {},
): UseFeatureFlagResult => {
  const [isEnabled, setIsEnabled] = useState<boolean>(defaultValue);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useContext(AuthContext);

  const evaluateFlag = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Check cache first
      const cacheKey = `${flagName}-${user?.id || "anonymous"}`;
      const cached = flagCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setIsEnabled(cached.value);
        setIsLoading(false);
        return;
      }

      // Build evaluation context
      const evaluationContext: FeatureFlagContext = {
        user_id: user?.id,
        environment: process.env.NODE_ENV || "development",
        ...context,
      };

      const requestData: FlagEvaluationRequest = {
        flag_name: flagName,
        context: evaluationContext,
        default_value: defaultValue,
      };

      const response = await httpClient.post<FlagEvaluationResponse>(
        "/api/feature-flags/evaluate",
        requestData,
      );

      const flagValue = response.data.flag_value;
      setIsEnabled(flagValue);

      // Cache the result
      flagCache.set(cacheKey, {
        value: flagValue,
        timestamp: Date.now(),
      });

      logger.info("Feature flag evaluated", {
        flagName,
        flagValue,
        userId: user?.id,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);
      setIsEnabled(defaultValue);

      logger.error("Feature flag evaluation failed", {
        flagName,
        error: errorMessage,
        userId: user?.id,
      });
    } finally {
      setIsLoading(false);
    }
  }, [flagName, defaultValue, context, user?.id]);

  useEffect(() => {
    evaluateFlag();
  }, [evaluateFlag]);

  return {
    isEnabled,
    isLoading,
    error,
    refetch: evaluateFlag,
  };
};

/**
 * Hook to get all feature flags for the current environment
 */
export const useAllFeatureFlags = (): UseAllFlagsResult => {
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useContext(AuthContext);

  const fetchAllFlags = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await httpClient.get<AllFlagsResponse>("/api/feature-flags/flags");

      setFlags(response.data.flags);

      logger.info("All feature flags fetched", {
        flagCount: Object.keys(response.data.flags).length,
        environment: response.data.environment,
        userId: user?.id,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);

      logger.error("Failed to fetch all feature flags", {
        error: errorMessage,
        userId: user?.id,
      });
    } finally {
      setIsLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchAllFlags();
  }, [fetchAllFlags]);

  return {
    flags,
    isLoading,
    error,
    refetch: fetchAllFlags,
  };
};

/**
 * Hook to get detailed information about a specific flag
 * @param flagName - Name of the feature flag
 */
export const useFeatureFlagInfo = (flagName: string) => {
  const [flagInfo, setFlagInfo] = useState<FlagInfo | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useContext(AuthContext);

  const fetchFlagInfo = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await httpClient.get<FlagInfo>(`/api/feature-flags/flags/${flagName}/info`);

      setFlagInfo(response.data);

      logger.info("Feature flag info fetched", {
        flagName,
        userId: user?.id,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);

      logger.error("Failed to fetch feature flag info", {
        flagName,
        error: errorMessage,
        userId: user?.id,
      });
    } finally {
      setIsLoading(false);
    }
  }, [flagName, user?.id]);

  useEffect(() => {
    fetchFlagInfo();
  }, [fetchFlagInfo]);

  return {
    flagInfo,
    isLoading,
    error,
    refetch: fetchFlagInfo,
  };
};

/**
 * Hook for kill switch flags - simplified interface for critical features
 * @param killSwitchType - Type of kill switch (video-calls, edi-integration, payments)
 */
export const useKillSwitch = (killSwitchType: string) => {
  const [isEnabled, setIsEnabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useContext(AuthContext);

  const checkKillSwitch = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await httpClient.get<{
        flag_name: string;
        enabled: boolean;
      }>(`/api/feature-flags/kill-switch/${killSwitchType}`);

      setIsEnabled(response.data.enabled);

      logger.info("Kill switch checked", {
        killSwitchType,
        enabled: response.data.enabled,
        userId: user?.id,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);
      setIsEnabled(false); // Default to disabled for kill switches

      logger.error("Kill switch check failed", {
        killSwitchType,
        error: errorMessage,
        userId: user?.id,
      });
    } finally {
      setIsLoading(false);
    }
  }, [killSwitchType, user?.id]);

  useEffect(() => {
    checkKillSwitch();
  }, [checkKillSwitch]);

  return {
    isEnabled,
    isLoading,
    error,
    refetch: checkKillSwitch,
  };
};

/**
 * Utility function to clear the local flag cache
 * Useful when you want to force a fresh evaluation
 */
export const clearFeatureFlagCache = (): void => {
  flagCache.clear();
  logger.info("Feature flag cache cleared");
};

/**
 * Higher-order component for conditional rendering based on feature flags
 * @param flagName - Name of the feature flag
 * @param defaultValue - Default value if flag evaluation fails
 * @param fallback - Component to render when flag is disabled
 */
export const withFeatureFlag = <P extends object>(
  flagName: string,
  defaultValue: boolean = false,
  fallback?: React.ComponentType<P> | null,
) => {
  return (WrappedComponent: React.ComponentType<P>) => {
    const FeatureFlagWrapper: React.FC<P> = (props) => {
      const { isEnabled, isLoading } = useFeatureFlag(flagName, defaultValue);

      if (isLoading) {
        return <div>Loading...</div>;
      }

      if (!isEnabled) {
        return fallback ? <fallback {...props} /> : null;
      }

      return <WrappedComponent {...props} />;
    };

    FeatureFlagWrapper.displayName = `withFeatureFlag(${
      WrappedComponent.displayName || WrappedComponent.name
    })`;

    return FeatureFlagWrapper;
  };
};
