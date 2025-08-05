/**
 * Frontend metrics collection utilities for performance and error tracking.
 * HIPAA-compliant with PHI scrubbing.
 */

import { scrubPHI } from "./phi-scrubber";
import { Logger } from "./logger";

export interface PerformanceMetric {
  name: string;
  value: number;
  timestamp: number;
  correlationId?: string;
  tags?: Record<string, string>;
}

export interface ErrorMetric {
  name: string;
  error: string;
  timestamp: number;
  correlationId?: string;
  component?: string;
  tags?: Record<string, string>;
}

export interface UserActionMetric {
  action: string;
  component: string;
  timestamp: number;
  correlationId?: string;
  duration?: number;
  success: boolean;
  tags?: Record<string, string>;
}

class MetricsCollector {
  private static instance: MetricsCollector;
  private metricsBuffer: (PerformanceMetric | ErrorMetric | UserActionMetric)[] = [];
  private flushInterval: number = 30000; // 30 seconds
  private maxBufferSize: number = 100;
  private isEnabled: boolean = true;

  private constructor() {
    this.startPeriodicFlush();
    this.setupPerformanceObserver();
  }

  static getInstance(): MetricsCollector {
    if (!MetricsCollector.instance) {
      MetricsCollector.instance = new MetricsCollector();
    }
    return MetricsCollector.instance;
  }

  /**
   * Enable or disable metrics collection
   */
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  /**
   * Record a performance metric
   */
  recordPerformance(name: string, value: number, tags?: Record<string, string>): void {
    if (!this.isEnabled) return;

    const metric: PerformanceMetric = {
      name: scrubPHI(name),
      value,
      timestamp: Date.now(),
      correlationId: Logger.getCorrelationId() || undefined,
      tags: tags ? scrubPHI(tags) : undefined,
    };

    this.addToBuffer(metric);
  }

  /**
   * Record an error metric
   */
  recordError(
    name: string,
    error: Error | string,
    component?: string,
    tags?: Record<string, string>,
  ): void {
    if (!this.isEnabled) return;

    const errorString = error instanceof Error ? error.message : error;
    const metric: ErrorMetric = {
      name: scrubPHI(name),
      error: scrubPHI(errorString),
      timestamp: Date.now(),
      correlationId: Logger.getCorrelationId() || undefined,
      component: component ? scrubPHI(component) : undefined,
      tags: tags ? scrubPHI(tags) : undefined,
    };

    this.addToBuffer(metric);

    // Also log the error
    Logger.error(`Metrics: ${name}`, error instanceof Error ? error : new Error(errorString), {
      component,
      ...tags,
    });
  }

  /**
   * Record a user action metric
   */
  recordUserAction(
    action: string,
    component: string,
    success: boolean = true,
    duration?: number,
    tags?: Record<string, string>,
  ): void {
    if (!this.isEnabled) return;

    const metric: UserActionMetric = {
      action: scrubPHI(action),
      component: scrubPHI(component),
      timestamp: Date.now(),
      correlationId: Logger.getCorrelationId() || undefined,
      duration,
      success,
      tags: tags ? scrubPHI(tags) : undefined,
    };

    this.addToBuffer(metric);

    // Also log the action for audit trail
    Logger.auditAction(action, component, "frontend-user", {
      success: success.toString(),
      duration: duration?.toString(),
      ...tags,
    });
  }

  /**
   * Record page load performance
   */
  recordPageLoad(pageName: string): void {
    if (!this.isEnabled || typeof window === "undefined") return;

    const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
    if (navigation) {
      this.recordPerformance("page_load_time", navigation.loadEventEnd - navigation.fetchStart, {
        page: pageName,
        type: "page_load",
      });

      this.recordPerformance(
        "dom_content_loaded",
        navigation.domContentLoadedEventEnd - navigation.fetchStart,
        {
          page: pageName,
          type: "dom_ready",
        },
      );

      this.recordPerformance("first_paint", navigation.responseEnd - navigation.fetchStart, {
        page: pageName,
        type: "first_paint",
      });
    }
  }

  /**
   * Record API call performance
   */
  recordApiCall(
    method: string,
    url: string,
    status: number,
    duration: number,
    success: boolean,
  ): void {
    if (!this.isEnabled) return;

    // Scrub PHI from URL
    const safeUrl = scrubPHI(url);

    this.recordPerformance("api_call_duration", duration, {
      method,
      url: safeUrl,
      status: status.toString(),
      success: success.toString(),
    });

    if (!success) {
      this.recordError("api_call_error", `API call failed: ${status}`, "api-client", {
        method,
        url: safeUrl,
        status: status.toString(),
      });
    }
  }

  /**
   * Add metric to buffer and flush if needed
   */
  private addToBuffer(metric: PerformanceMetric | ErrorMetric | UserActionMetric): void {
    this.metricsBuffer.push(metric);

    if (this.metricsBuffer.length >= this.maxBufferSize) {
      this.flush();
    }
  }

  /**
   * Flush metrics to backend
   */
  private async flush(): Promise<void> {
    if (this.metricsBuffer.length === 0) return;

    const metricsToSend = [...this.metricsBuffer];
    this.metricsBuffer = [];

    try {
      await fetch("/api/metrics/frontend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Correlation-ID": Logger.getCorrelationId() || Logger.generateCorrelationId(),
        },
        body: JSON.stringify({
          metrics: metricsToSend,
          timestamp: Date.now(),
        }),
      });
    } catch (error) {
      // Log metrics flush errors for debugging and monitoring
      Logger.error("Failed to send metrics to backend", error as Error, {
        correlationId: Logger.getCorrelationId() || Logger.generateCorrelationId(),
        metricsCount: metricsToSend.length,
      });
    }
  }

  /**
   * Start periodic flushing of metrics
   */
  private startPeriodicFlush(): void {
    setInterval(() => {
      this.flush();
    }, this.flushInterval);
  }

  /**
   * Setup Performance Observer for automatic performance tracking
   */
  private setupPerformanceObserver(): void {
    if (typeof window === "undefined" || !("PerformanceObserver" in window)) {
      return;
    }

    try {
      // Observe Long Tasks (performance issues)
      const longTaskObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) {
            // Tasks longer than 50ms
            this.recordPerformance("long_task", entry.duration, {
              type: "long_task",
              name: entry.name,
            });
          }
        }
      });
      longTaskObserver.observe({ entryTypes: ["longtask"] });

      // Observe Layout Shifts (CLS)
      const layoutShiftObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const layoutShiftEntry = entry as any; // LayoutShift interface not in standard types
          if (!layoutShiftEntry.hadRecentInput) {
            this.recordPerformance("layout_shift", layoutShiftEntry.value, {
              type: "layout_shift",
            });
          }
        }
      });
      layoutShiftObserver.observe({ entryTypes: ["layout-shift"] });
    } catch (error) {
      // Performance Observer not supported or failed to setup
      console.warn("Performance Observer setup failed:", error);
    }
  }
}

// Export singleton instance
export const metrics = MetricsCollector.getInstance();

// Convenience functions
export const recordPerformance = (name: string, value: number, tags?: Record<string, string>) => {
  metrics.recordPerformance(name, value, tags);
};

export const recordError = (
  name: string,
  error: Error | string,
  component?: string,
  tags?: Record<string, string>,
) => {
  metrics.recordError(name, error, component, tags);
};

export const recordUserAction = (
  action: string,
  component: string,
  success: boolean = true,
  duration?: number,
  tags?: Record<string, string>,
) => {
  metrics.recordUserAction(action, component, success, duration, tags);
};

export const recordPageLoad = (pageName: string) => {
  metrics.recordPageLoad(pageName);
};

export const recordApiCall = (
  method: string,
  url: string,
  status: number,
  duration: number,
  success: boolean,
) => {
  metrics.recordApiCall(method, url, status, duration, success);
};

// Enable/disable metrics collection
export const setMetricsEnabled = (enabled: boolean) => {
  metrics.setEnabled(enabled);
};
