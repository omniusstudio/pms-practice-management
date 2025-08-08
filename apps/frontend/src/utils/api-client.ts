/**
 * Enhanced API client utilities for HIPAA-compliant Practice Management System
 * Implements standardized error handling, pagination, and request patterns
 */

// Note: Install uuid package: npm install uuid @types/uuid
// import { v4 as uuidv4 } from 'uuid';

// Temporary UUID implementation until package is installed
const uuidv4 = (): string => {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

// Import types from shared package
// Note: Ensure @pms/shared-types package is properly configured
interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status_code: number;
  correlation_id?: string;
}

interface PaginatedResponse<T = any> {
  data: T[];
  pagination: PaginationMeta;
  message?: string;
  status_code: number;
  correlation_id?: string;
}

interface ApiError {
  error: string;
  message: string;
  status_code: number;
  correlation_id?: string;
  details?: any;
}

interface ValidationErrorDetails {
  errors: Record<string, string[]>;
}

interface AuthorizationErrorDetails {
  required_permissions: string[];
  user_permissions: string[];
}

interface RateLimitErrorDetails {
  limit: number;
  remaining: number;
  reset_time: string;
  retry_after: number;
}

interface ServiceErrorDetails {
  service: string;
  error_code: string;
}

interface PaginationMeta {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
const API_VERSION = "v1";

// Request configuration interface
interface RequestConfig {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  headers?: Record<string, string>;
  body?: any;
  requiresAuth?: boolean;
  idempotencyKey?: string;
  timeout?: number;
}

// Pagination parameters
interface PaginationParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// Enhanced API error class
export class ApiClientError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly correlationId?: string;
  public readonly details?: any;
  public readonly timestamp: string;

  constructor(
    message: string,
    status: number,
    code: string,
    correlationId?: string,
    details?: any,
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
    this.details = details;
    this.timestamp = new Date().toISOString();
  }

  // Check if error is a specific type
  isValidationError(): boolean {
    return this.status === 422;
  }

  isAuthenticationError(): boolean {
    return this.status === 401;
  }

  isAuthorizationError(): boolean {
    return this.status === 403;
  }

  isNotFoundError(): boolean {
    return this.status === 404;
  }

  isRateLimitError(): boolean {
    return this.status === 429;
  }

  isServerError(): boolean {
    return this.status >= 500;
  }
}

// API client class
export class ApiClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;
  private authToken?: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = `${baseUrl}/api/${API_VERSION}`;
    this.defaultHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Client-Version": process.env.REACT_APP_VERSION || "1.0.0",
    };
  }

  // Set authentication token
  setAuthToken(token: string): void {
    this.authToken = token;
  }

  // Clear authentication token
  clearAuthToken(): void {
    this.authToken = undefined;
  }

  // Generate correlation ID for request tracking
  private generateCorrelationId(): string {
    return uuidv4();
  }

  // Build request headers
  private buildHeaders(config: RequestConfig): Record<string, string> {
    const headers: Record<string, string> = {
      ...this.defaultHeaders,
      ...config.headers,
      "X-Correlation-ID": this.generateCorrelationId(),
    };

    // Add authentication header if required
    if (config.requiresAuth && this.authToken) {
      headers["Authorization"] = `Bearer ${this.authToken}`;
    }

    // Add idempotency key for non-GET requests
    if (config.idempotencyKey && config.method !== "GET") {
      headers["Idempotency-Key"] = config.idempotencyKey;
    }

    return headers;
  }

  // Parse error response
  private async parseErrorResponse(response: Response): Promise<ApiClientError> {
    let errorData: ApiError;

    try {
      errorData = await response.json();
    } catch {
      // Fallback for non-JSON error responses
      errorData = {
        error: "Unknown error",
        message: `HTTP ${response.status}: ${response.statusText}`,
        status_code: response.status,
        correlation_id: response.headers.get("X-Correlation-ID") || undefined,
      };
    }

    return new ApiClientError(
      errorData.message,
      errorData.status_code,
      errorData.error,
      errorData.correlation_id,
      errorData.details,
    );
  }

  // Make HTTP request
  private async makeRequest<T>(endpoint: string, config: RequestConfig): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = this.buildHeaders(config);

    const requestOptions: RequestInit = {
      method: config.method,
      headers,
      ...(config.body && { body: JSON.stringify(config.body) }),
    };

    // Add timeout if specified
    const controller = new AbortController();
    if (config.timeout) {
      setTimeout(() => controller.abort(), config.timeout);
      requestOptions.signal = controller.signal;
    }

    try {
      const response = await fetch(url, requestOptions);

      if (!response.ok) {
        throw await this.parseErrorResponse(response);
      }

      // Handle empty responses (e.g., 204 No Content)
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }

      // Handle network errors, timeouts, etc.
      throw new ApiClientError(
        error instanceof Error ? error.message : "Network error",
        0,
        "NETWORK_ERROR",
        undefined,
        { originalError: error },
      );
    }
  }

  // GET request
  async get<T>(
    endpoint: string,
    params?: Record<string, any>,
    config: Partial<RequestConfig> = {},
  ): Promise<T> {
    let url = endpoint;

    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      url += `?${searchParams.toString()}`;
    }

    return this.makeRequest<T>(url, {
      method: "GET",
      requiresAuth: true,
      ...config,
    });
  }

  // POST request
  async post<T>(endpoint: string, data?: any, config: Partial<RequestConfig> = {}): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: "POST",
      body: data,
      requiresAuth: true,
      idempotencyKey: config.idempotencyKey || uuidv4(),
      ...config,
    });
  }

  // PUT request
  async put<T>(endpoint: string, data?: any, config: Partial<RequestConfig> = {}): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: "PUT",
      body: data,
      requiresAuth: true,
      idempotencyKey: config.idempotencyKey || uuidv4(),
      ...config,
    });
  }

  // PATCH request
  async patch<T>(endpoint: string, data?: any, config: Partial<RequestConfig> = {}): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: "PATCH",
      body: data,
      requiresAuth: true,
      idempotencyKey: config.idempotencyKey || uuidv4(),
      ...config,
    });
  }

  // DELETE request
  async delete<T>(endpoint: string, config: Partial<RequestConfig> = {}): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: "DELETE",
      requiresAuth: true,
      idempotencyKey: config.idempotencyKey || uuidv4(),
      ...config,
    });
  }

  // Paginated GET request
  async getPaginated<T>(
    endpoint: string,
    pagination: PaginationParams = {},
    filters?: Record<string, any>,
    config: Partial<RequestConfig> = {},
  ): Promise<PaginatedResponse<T>> {
    const params = {
      page: pagination.page || 1,
      per_page: pagination.per_page || 20,
      ...(pagination.sort_by && { sort_by: pagination.sort_by }),
      ...(pagination.sort_order && { sort_order: pagination.sort_order }),
      ...filters,
    };

    return this.get<PaginatedResponse<T>>(endpoint, params, config);
  }
}

// Default API client instance
export const apiClient = new ApiClient();

// Utility functions for common operations
export const apiUtils = {
  // Generate idempotency key
  generateIdempotencyKey: (): string => uuidv4(),

  // Check if error is retryable
  isRetryableError: (error: ApiClientError): boolean => {
    return error.isServerError() || error.isRateLimitError();
  },

  // Get retry delay for rate limit errors
  getRetryDelay: (error: ApiClientError): number => {
    if (error.isRateLimitError() && error.details?.retry_after) {
      return error.details.retry_after * 1000; // Convert to milliseconds
    }
    return 1000; // Default 1 second
  },

  // Format validation errors for display
  formatValidationErrors: (error: ApiClientError): string[] => {
    if (!error.isValidationError() || !error.details?.errors) {
      return [error.message];
    }

    const errors: string[] = [];
    Object.entries(error.details.errors).forEach(([field, messages]) => {
      if (Array.isArray(messages)) {
        messages.forEach((message) => {
          errors.push(`${field}: ${message}`);
        });
      } else {
        errors.push(`${field}: ${messages}`);
      }
    });

    return errors;
  },
};

// Export types for external use
export type {
  RequestConfig,
  PaginationParams,
  ApiResponse,
  PaginatedResponse,
  ApiError,
  ValidationErrorDetails,
  AuthorizationErrorDetails,
  RateLimitErrorDetails,
  ServiceErrorDetails,
  PaginationMeta,
};
