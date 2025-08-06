/**
 * HTTP client with correlation ID support and request/response logging.
 */

import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from "axios";
import { Logger } from "./logger";
import { scrubPHIFromURL } from "./phi-scrubber";

/**
 * Generate a correlation ID for client requests
 */
function generateCorrelationId(): string {
  return `client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Create HTTP client with correlation ID and logging support
 */
export function createHttpClient(baseURL?: string): AxiosInstance {
  // Use environment variable if available, otherwise fall back to provided baseURL or default
  const apiUrl = import.meta.env.VITE_API_URL || baseURL || "/api";

  const client = axios.create({
    baseURL: apiUrl,
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // Request interceptor - add correlation ID and log requests
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Generate or use existing correlation ID
      const correlationId = Logger.getCorrelationId() || generateCorrelationId();

      // Add correlation ID to headers
      if (config.headers) {
        config.headers["X-Correlation-ID"] = correlationId;
      }

      // Update logger correlation ID
      Logger.setCorrelationId(correlationId);

      // Log the request (PHI-safe)
      Logger.info("HTTP Request Started", {
        correlationId,
        method: config.method?.toUpperCase(),
        url: scrubPHIFromURL(config.url || ""),
        hasData: !!config.data,
      });

      return config;
    },
    (error) => {
      Logger.error("HTTP Request Error", error, {
        correlationId: Logger.getCorrelationId() || "unknown",
      });
      return Promise.reject(error);
    },
  );

  // Response interceptor - log responses and handle correlation IDs
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      const startTime = Date.now();
      const correlationId = response.headers["x-correlation-id"] || Logger.getCorrelationId();

      // Update correlation ID from response
      if (response.headers["x-correlation-id"]) {
        Logger.setCorrelationId(response.headers["x-correlation-id"]);
      }

      // Log successful response
      Logger.apiCall(
        response.config.method?.toUpperCase() || "GET",
        scrubPHIFromURL(response.config.url || ""),
        response.status,
        Date.now() - startTime,
        {
          correlationId,
          responseSize: JSON.stringify(response.data).length,
        },
      );

      return response;
    },
    (error) => {
      const correlationId =
        error.response?.headers?.["x-correlation-id"] || Logger.getCorrelationId();

      // Log error response
      Logger.error("HTTP Response Error", error, {
        correlationId,
        status: error.response?.status,
        method: error.config?.method?.toUpperCase(),
        url: scrubPHIFromURL(error.config?.url || ""),
      });

      return Promise.reject(error);
    },
  );

  return client;
}

// Default HTTP client instance
export const httpClient = createHttpClient();

/**
 * Wrapper functions for common HTTP methods with built-in logging
 */
export const api = {
  get: async <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await httpClient.get<T>(url, config);
    return response.data;
  },

  post: async <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    const response = await httpClient.post<T>(url, data, config);
    return response.data;
  },

  put: async <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    const response = await httpClient.put<T>(url, data, config);
    return response.data;
  },

  delete: async <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await httpClient.delete<T>(url, config);
    return response.data;
  },

  patch: async <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    const response = await httpClient.patch<T>(url, data, config);
    return response.data;
  },
};

/**
 * Hook for React components to use the HTTP client
 */
export const useHttpClient = () => {
  return {
    client: httpClient,
    api,
    generateCorrelationId,
  };
};
