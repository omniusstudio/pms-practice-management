/**
 * React hook for metrics collection in components.
 * Provides easy integration with component lifecycle and user interactions.
 */

import { useEffect, useCallback, useRef } from "react";
import { metrics, recordUserAction, recordError, recordPerformance } from "../utils/metrics";

export interface UseMetricsOptions {
  componentName: string;
  trackMount?: boolean;
  trackUnmount?: boolean;
  trackRenders?: boolean;
}

export interface MetricsHookReturn {
  trackAction: (
    action: string,
    success?: boolean,
    duration?: number,
    tags?: Record<string, string>
  ) => void;
  trackError: (error: Error | string, tags?: Record<string, string>) => void;
  trackPerformance: (name: string, value: number, tags?: Record<string, string>) => void;
  startTimer: (name: string) => () => number;
  trackAsyncAction: <T>(
    action: string,
    promise: Promise<T>,
    tags?: Record<string, string>
  ) => Promise<T>;
}

/**
 * Hook for component-level metrics tracking
 */
export const useMetrics = (options: UseMetricsOptions): MetricsHookReturn => {
  const { componentName, trackMount = true, trackUnmount = true, trackRenders = false } = options;
  const renderCount = useRef(0);
  const mountTime = useRef<number>(0);

  // Track component mount
  useEffect(() => {
    mountTime.current = Date.now();

    if (trackMount) {
      recordUserAction("component_mount", componentName, true, undefined, {
        timestamp: mountTime.current.toString(),
      });
    }

    // Track component unmount
    return () => {
      if (trackUnmount) {
        const lifetime = Date.now() - mountTime.current;
        recordUserAction("component_unmount", componentName, true, lifetime, {
          lifetime: lifetime.toString(),
        });
      }
    };
  }, [componentName, trackMount, trackUnmount]);

  // Track renders
  useEffect(() => {
    renderCount.current += 1;

    if (trackRenders && renderCount.current > 1) {
      recordPerformance("component_render", renderCount.current, {
        component: componentName,
        render_count: renderCount.current.toString(),
      });
    }
  });

  // Track user action
  const trackAction = useCallback(
    (action: string, success: boolean = true, duration?: number, tags?: Record<string, string>) => {
      recordUserAction(action, componentName, success, duration, {
        ...tags,
        component: componentName,
      });
    },
    [componentName]
  );

  // Track error
  const trackError = useCallback(
    (error: Error | string, tags?: Record<string, string>) => {
      recordError("component_error", error, componentName, {
        ...tags,
        component: componentName,
      });
    },
    [componentName]
  );

  // Track performance metric
  const trackPerformance = useCallback(
    (name: string, value: number, tags?: Record<string, string>) => {
      recordPerformance(name, value, {
        ...tags,
        component: componentName,
      });
    },
    [componentName]
  );

  // Start a timer and return a function to end it
  const startTimer = useCallback(
    (name: string) => {
      const startTime = Date.now();
      return () => {
        const duration = Date.now() - startTime;
        trackPerformance(name, duration, {
          type: "timer",
        });
        return duration;
      };
    },
    [trackPerformance]
  );

  // Track async action with automatic success/error handling
  const trackAsyncAction = useCallback(
    async <T>(action: string, promise: Promise<T>, tags?: Record<string, string>): Promise<T> => {
      const startTime = Date.now();

      try {
        const result = await promise;
        const duration = Date.now() - startTime;

        trackAction(action, true, duration, {
          ...tags,
          async: "true",
        });

        return result;
      } catch (error) {
        const duration = Date.now() - startTime;

        trackAction(action, false, duration, {
          ...tags,
          async: "true",
        });

        trackError(error instanceof Error ? error : new Error(String(error)), {
          ...tags,
          action,
          async: "true",
        });

        throw error;
      }
    },
    [trackAction, trackError]
  );

  return {
    trackAction,
    trackError,
    trackPerformance,
    startTimer,
    trackAsyncAction,
  };
};

/**
 * Hook for page-level metrics tracking
 */
export const usePageMetrics = (pageName: string) => {
  const metricsHook = useMetrics({
    componentName: `page_${pageName}`,
    trackMount: true,
    trackUnmount: true,
    trackRenders: false,
  });

  useEffect(() => {
    // Track page load performance
    const timer = setTimeout(() => {
      metrics.recordPageLoad(pageName);
    }, 100); // Small delay to ensure page is fully loaded

    return () => clearTimeout(timer);
  }, [pageName]);

  return metricsHook;
};

/**
 * Hook for form metrics tracking
 */
export const useFormMetrics = (formName: string) => {
  const metricsHook = useMetrics({
    componentName: `form_${formName}`,
    trackMount: true,
    trackUnmount: false,
    trackRenders: false,
  });

  const trackFieldInteraction = useCallback(
    (fieldName: string, interactionType: "focus" | "blur" | "change") => {
      metricsHook.trackAction(`field_${interactionType}`, true, undefined, {
        field: fieldName,
        form: formName,
      });
    },
    [metricsHook, formName]
  );

  const trackFormSubmission = useCallback(
    (success: boolean, validationErrors?: string[]) => {
      metricsHook.trackAction("form_submit", success, undefined, {
        form: formName,
        validation_errors: validationErrors?.length?.toString() || "0",
      });

      if (validationErrors && validationErrors.length > 0) {
        metricsHook.trackError(`Form validation failed: ${validationErrors.join(", ")}`, {
          form: formName,
          error_count: validationErrors.length.toString(),
        });
      }
    },
    [metricsHook, formName]
  );

  const trackFormReset = useCallback(() => {
    metricsHook.trackAction("form_reset", true, undefined, {
      form: formName,
    });
  }, [metricsHook, formName]);

  return {
    ...metricsHook,
    trackFieldInteraction,
    trackFormSubmission,
    trackFormReset,
  };
};

/**
 * Hook for API call metrics tracking
 */
export const useApiMetrics = () => {
  const trackApiCall = useCallback(
    async <T>(method: string, url: string, apiCall: () => Promise<T>): Promise<T> => {
      const startTime = Date.now();

      try {
        const result = await apiCall();
        const duration = Date.now() - startTime;

        metrics.recordApiCall(method, url, 200, duration, true);

        return result;
      } catch (error: any) {
        const duration = Date.now() - startTime;
        const status = error?.response?.status || 500;

        metrics.recordApiCall(method, url, status, duration, false);

        throw error;
      }
    },
    []
  );

  return { trackApiCall };
};
