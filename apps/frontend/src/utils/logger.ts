/**
 * Client-side logging utilities with PHI scrubbing and correlation ID support.
 */

import { scrubPHI } from "./phi-scrubber";

export interface LogContext {
  correlationId?: string;
  userId?: string;
  component?: string;
  action?: string;
  [key: string]: any;
}

export class Logger {
  private static correlationId: string | null = null;

  /**
   * Set the correlation ID for subsequent log entries
   */
  static setCorrelationId(id: string): void {
    this.correlationId = id;
  }

  /**
   * Get the current correlation ID
   */
  static getCorrelationId(): string | null {
    return this.correlationId;
  }

  /**
   * Generate a new correlation ID
   */
  static generateCorrelationId(): string {
    return `client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Log an info message (PHI-safe)
   */
  static info(message: string, context?: LogContext): void {
    this.log("info", message, context);
  }

  /**
   * Log a warning message (PHI-safe)
   */
  static warn(message: string, context?: LogContext): void {
    this.log("warn", message, context);
  }

  /**
   * Log an error message (PHI-safe)
   */
  static error(message: string, error?: Error, context?: LogContext): void {
    const errorContext = {
      ...context,
      error: error
        ? {
            name: error.name,
            message: scrubPHI(error.message),
            // Don't include stack trace to avoid PHI exposure
          }
        : undefined,
    };
    this.log("error", message, errorContext);
  }

  /**
   * Log user action for audit trail
   */
  static auditAction(action: string, resource: string, userId: string, context?: LogContext): void {
    const auditContext = {
      ...context,
      event: "user_action",
      action,
      resource,
      userId,
      timestamp: new Date().toISOString(),
    };
    this.log("info", `User Action: ${action} ${resource}`, auditContext);
  }

  /**
   * Log API request/response for debugging
   */
  static apiCall(
    method: string,
    url: string,
    status: number,
    duration: number,
    context?: LogContext,
  ): void {
    const apiContext = {
      ...context,
      event: "api_call",
      method,
      url: scrubPHI(url), // Scrub any PHI from URL
      status,
      duration,
      timestamp: new Date().toISOString(),
    };
    this.log("info", `API Call: ${method} ${url}`, apiContext);
  }

  /**
   * Core logging method
   */
  private static log(level: string, message: string, context?: LogContext): void {
    const logEntry = {
      level,
      message: scrubPHI(message),
      correlationId: context?.correlationId || this.correlationId,
      timestamp: new Date().toISOString(),
      ...scrubPHI(context || {}),
    };

    // In development, also log to console
    if (process.env.NODE_ENV === "development") {
      /* eslint-disable no-console */
      const consoleMethod =
        level === "error" ? console.error : level === "warn" ? console.warn : console.log;
      consoleMethod("[PMS]", logEntry);
      /* eslint-enable no-console */
    }

    // In production, send to logging service
    if (process.env.NODE_ENV === "production") {
      this.sendToLoggingService(logEntry);
    }
  }

  /**
   * Send log entry to backend logging service
   */
  private static async sendToLoggingService(logEntry: any): Promise<void> {
    try {
      await fetch("/api/logs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Correlation-ID": logEntry.correlationId || this.generateCorrelationId(),
        },
        body: JSON.stringify(logEntry),
      });
    } catch (error) {
      // Fallback to console if logging service is unavailable
      console.error("[PMS] Failed to send log to service:", error);
    }
  }
}

/**
 * Hook for React components to use logging
 */
export const useLogger = () => {
  return {
    info: Logger.info.bind(Logger),
    warn: Logger.warn.bind(Logger),
    error: Logger.error.bind(Logger),
    auditAction: Logger.auditAction.bind(Logger),
    apiCall: Logger.apiCall.bind(Logger),
    setCorrelationId: Logger.setCorrelationId.bind(Logger),
    getCorrelationId: Logger.getCorrelationId.bind(Logger),
  };
};
