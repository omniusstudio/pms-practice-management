/**
 * Sentry service for client-side error tracking with PHI scrubbing
 */

import * as Sentry from "@sentry/react";
import { BrowserTracing } from "@sentry/tracing";
import { scrubPHI } from "../utils/phiScrubber";

// PHI patterns for client-side scrubbing
const PHI_PATTERNS = [
  // SSN patterns
  /\b\d{3}-\d{2}-\d{4}\b/g,
  /\b\d{9}\b/g,
  // Phone numbers
  /\b\d{3}-\d{3}-\d{4}\b/g,
  /\(\d{3}\)\s*\d{3}-\d{4}/g,
  // Email addresses
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
  // Date of birth patterns
  /\b\d{1,2}\/\d{1,2}\/\d{4}\b/g,
  /\b\d{4}-\d{2}-\d{2}\b/g,
  // Medical record numbers
  /\bMRN[:\s]*\d+/gi,
  /\bMedical Record[:\s]*\d+/gi,
  // Patient names (common patterns)
  /\bPatient[:\s]+[A-Za-z]+\s+[A-Za-z]+/gi,
  /\bDOB[:\s]+\d{1,2}\/\d{1,2}\/\d{4}/gi,
];

/**
 * Scrub PHI from text content
 */
function scrubPHIFromText(text: string): string {
  let scrubbed = text;

  PHI_PATTERNS.forEach((pattern) => {
    scrubbed = scrubbed.replace(pattern, "[REDACTED]");
  });

  return scrubbed;
}

/**
 * Scrub PHI from Sentry event data
 */
function scrubSentryEvent(event: Sentry.Event): Sentry.Event {
  // Scrub exception messages
  if (event.exception?.values) {
    event.exception.values.forEach((exception) => {
      if (exception.value) {
        exception.value = scrubPHIFromText(exception.value);
      }

      // Scrub stack trace
      if (exception.stacktrace?.frames) {
        exception.stacktrace.frames.forEach((frame) => {
          if (frame.filename) {
            frame.filename = scrubPHIFromText(frame.filename);
          }
          if (frame.function) {
            frame.function = scrubPHIFromText(frame.function);
          }
          if (frame.vars) {
            Object.keys(frame.vars).forEach((key) => {
              if (typeof frame.vars![key] === "string") {
                frame.vars![key] = scrubPHIFromText(frame.vars![key]);
              }
            });
          }
        });
      }
    });
  }

  // Scrub message
  if (event.message) {
    event.message = scrubPHIFromText(event.message);
  }

  // Scrub breadcrumbs
  if (event.breadcrumbs) {
    event.breadcrumbs.forEach((breadcrumb) => {
      if (breadcrumb.message) {
        breadcrumb.message = scrubPHIFromText(breadcrumb.message);
      }
      if (breadcrumb.data) {
        Object.keys(breadcrumb.data).forEach((key) => {
          if (typeof breadcrumb.data![key] === "string") {
            breadcrumb.data![key] = scrubPHIFromText(breadcrumb.data![key]);
          }
        });
      }
    });
  }

  // Scrub request data
  if (event.request) {
    if (event.request.url) {
      event.request.url = scrubPHIFromText(event.request.url);
    }
    if (event.request.query_string) {
      event.request.query_string = scrubPHIFromText(event.request.query_string);
    }
    if (event.request.data) {
      if (typeof event.request.data === "string") {
        event.request.data = scrubPHIFromText(event.request.data);
      }
    }

    // Remove sensitive headers
    if (event.request.headers) {
      const sensitiveHeaders = ["authorization", "cookie", "x-api-key"];
      sensitiveHeaders.forEach((header) => {
        if (event.request!.headers![header]) {
          event.request!.headers![header] = "[REDACTED]";
        }
      });
    }
  }

  // Scrub user data (anonymize)
  if (event.user) {
    if (event.user.id) {
      // Hash user ID for anonymization
      const userHash = Math.abs(hashCode(event.user.id.toString())) % 10000;
      event.user.id = `user_${userHash.toString().padStart(4, "0")}`;
    }

    // Remove sensitive user fields
    delete event.user.email;
    delete event.user.username;
    delete event.user.ip_address;
  }

  // Scrub extra context
  if (event.extra) {
    Object.keys(event.extra).forEach((key) => {
      if (typeof event.extra![key] === "string") {
        event.extra![key] = scrubPHIFromText(event.extra![key]);
      }
    });
  }

  return event;
}

/**
 * Simple hash function for anonymization
 */
function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return hash;
}

/**
 * Initialize Sentry for the React application
 */
export function initSentry(): void {
  const dsn = process.env.REACT_APP_SENTRY_DSN;
  const environment = process.env.REACT_APP_SENTRY_ENVIRONMENT || "development";
  const release = process.env.REACT_APP_SENTRY_RELEASE;

  if (!dsn) {
    console.warn("Sentry DSN not configured, error tracking disabled");
    return;
  }

  Sentry.init({
    dsn,
    environment,
    release,
    integrations: [
      new BrowserTracing({
        // Trace navigation and user interactions
        routingInstrumentation: Sentry.reactRouterV6Instrumentation(
          React.useEffect,
          useLocation,
          useNavigationType,
          createRoutesFromChildren,
          matchRoutes,
        ),
      }),
    ],

    // Performance monitoring
    tracesSampleRate: parseFloat(process.env.REACT_APP_SENTRY_TRACES_SAMPLE_RATE || "0.1"),

    // Session replay (disabled for HIPAA compliance)
    replaysSessionSampleRate: 0.0,
    replaysOnErrorSampleRate: 0.0,

    // PHI scrubbing before send
    beforeSend(event) {
      return scrubSentryEvent(event);
    },

    // Additional configuration
    debug: environment === "development",

    // Ignore common non-critical errors
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "Non-Error promise rejection captured",
      "ChunkLoadError",
      "Loading chunk",
      "Network Error",
    ],

    // Set initial user context (anonymized)
    initialScope: {
      tags: {
        component: "pms-frontend",
      },
    },
  });

  console.log(`Sentry initialized for environment: ${environment}`);
}

/**
 * Set user context with anonymization
 */
export function setSentryUser(userId: string, additionalData?: Record<string, any>): void {
  Sentry.setUser({
    id: `user_${Math.abs(hashCode(userId)) % 10000}`,
    ...additionalData,
  });
}

/**
 * Add breadcrumb with PHI scrubbing
 */
export function addSentryBreadcrumb(
  message: string,
  category: string = "custom",
  level: Sentry.SeverityLevel = "info",
  data?: Record<string, any>,
): void {
  Sentry.addBreadcrumb({
    message: scrubPHIFromText(message),
    category,
    level,
    data: data ? scrubPHIFromText(JSON.stringify(data)) : undefined,
  });
}

/**
 * Capture exception with PHI scrubbing
 */
export function captureSentryException(error: Error, context?: Record<string, any>): void {
  Sentry.withScope((scope) => {
    if (context) {
      Object.keys(context).forEach((key) => {
        const value = context[key];
        const scrubbed = typeof value === "string" ? scrubPHIFromText(value) : value;
        scope.setContext(key, scrubbed);
      });
    }

    Sentry.captureException(error);
  });
}

/**
 * Capture message with PHI scrubbing
 */
export function captureSentryMessage(
  message: string,
  level: Sentry.SeverityLevel = "info",
  context?: Record<string, any>,
): void {
  Sentry.withScope((scope) => {
    if (context) {
      Object.keys(context).forEach((key) => {
        const value = context[key];
        const scrubbed = typeof value === "string" ? scrubPHIFromText(value) : value;
        scope.setContext(key, scrubbed);
      });
    }

    Sentry.captureMessage(scrubPHIFromText(message), level);
  });
}

/**
 * Create test error for validation
 */
export function createSentryTestError(): void {
  const testError = new Error(
    "Test error for Sentry validation. PHI test: Patient John Doe SSN 123-45-6789",
  );

  captureSentryException(testError, {
    test_type: "sentry_validation",
    timestamp: Date.now(),
    test_data: "Patient: Jane Smith, DOB: 1990-01-01",
  });
}

// Import React Router hooks (these would be imported from react-router-dom)
// This is a placeholder - actual imports would be:
// import { useEffect } from 'react';
// import { useLocation, useNavigationType, createRoutesFromChildren, matchRoutes } from 'react-router-dom';
const React = { useEffect: () => {} };
const useLocation = () => ({});
const useNavigationType = () => "POP";
const createRoutesFromChildren = () => [];
const matchRoutes = () => [];
