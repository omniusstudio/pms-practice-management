/**
 * React hooks for API integration with standardized error handling and loading states
 * Implements HIPAA-compliant Practice Management System API patterns
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient, ApiClientError, apiUtils } from "../utils/api-client";

// Hook state interfaces
interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiClientError | null;
  correlationId?: string;
}

interface UsePaginatedApiState<T> {
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  } | null;
  loading: boolean;
  error: ApiClientError | null;
  correlationId?: string;
}

interface UseMutationState<T> {
  data: T | null;
  loading: boolean;
  error: ApiClientError | null;
  correlationId?: string;
}

// Options for API hooks
interface UseApiOptions {
  immediate?: boolean;
  retryAttempts?: number;
  retryDelay?: number;
  onSuccess?: (data: any) => void;
  onError?: (error: ApiClientError) => void;
}

interface UsePaginatedApiOptions extends UseApiOptions {
  initialPage?: number;
  initialPerPage?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

interface UseMutationOptions {
  onSuccess?: (data: any) => void;
  onError?: (error: ApiClientError) => void;
  showSuccessMessage?: boolean;
  showErrorMessage?: boolean;
}

/**
 * Hook for making GET requests with automatic loading states and error handling
 */
export function useApi<T>(
  endpoint: string,
  params?: Record<string, any>,
  options: UseApiOptions = {},
): UseApiState<T> & {
  refetch: () => Promise<void>;
  reset: () => void;
} {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);

  const { immediate = true, retryAttempts = 0, retryDelay = 1000, onSuccess, onError } = options;

  const fetchData = useCallback(async () => {
    // Cancel previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await apiClient.get<T>(endpoint, params, {
        timeout: 30000, // 30 second timeout
      });

      setState({
        data: response,
        loading: false,
        error: null,
        correlationId: (response as any)?.correlation_id,
      });

      retryCountRef.current = 0;
      onSuccess?.(response);
    } catch (error) {
      const apiError = error as ApiClientError;

      // Retry logic for retryable errors
      if (retryCountRef.current < retryAttempts && apiUtils.isRetryableError(apiError)) {
        retryCountRef.current++;
        const delay = apiError.isRateLimitError() ? apiUtils.getRetryDelay(apiError) : retryDelay;

        setTimeout(() => {
          fetchData();
        }, delay);
        return;
      }

      setState({
        data: null,
        loading: false,
        error: apiError,
        correlationId: apiError.correlationId,
      });

      retryCountRef.current = 0;
      onError?.(apiError);
    }
  }, [endpoint, params, retryAttempts, retryDelay, onSuccess, onError]);

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
    });
    retryCountRef.current = 0;
  }, []);

  useEffect(() => {
    if (immediate) {
      fetchData();
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData, immediate]);

  return {
    ...state,
    refetch: fetchData,
    reset,
  };
}

/**
 * Hook for paginated API requests with navigation controls
 */
export function usePaginatedApi<T>(
  endpoint: string,
  filters?: Record<string, any>,
  options: UsePaginatedApiOptions = {},
): UsePaginatedApiState<T> & {
  nextPage: () => void;
  prevPage: () => void;
  goToPage: (page: number) => void;
  setPerPage: (perPage: number) => void;
  setSorting: (sortBy: string, sortOrder: "asc" | "desc") => void;
  refetch: () => Promise<void>;
  reset: () => void;
} {
  const {
    initialPage = 1,
    initialPerPage = 20,
    sortBy,
    sortOrder = "asc",
    ...apiOptions
  } = options;

  const [state, setState] = useState<UsePaginatedApiState<T>>({
    data: [],
    pagination: null,
    loading: false,
    error: null,
  });

  const [paginationParams, setPaginationParams] = useState({
    page: initialPage,
    per_page: initialPerPage,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);

  const fetchData = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await apiClient.getPaginated<T>(endpoint, paginationParams, filters, {
        timeout: 30000,
      });

      setState({
        data: response.data,
        pagination: response.pagination,
        loading: false,
        error: null,
        correlationId: response.correlation_id,
      });

      retryCountRef.current = 0;
      apiOptions.onSuccess?.(response);
    } catch (error) {
      const apiError = error as ApiClientError;

      // Retry logic
      if (
        retryCountRef.current < (apiOptions.retryAttempts || 0) &&
        apiUtils.isRetryableError(apiError)
      ) {
        retryCountRef.current++;
        const delay = apiError.isRateLimitError()
          ? apiUtils.getRetryDelay(apiError)
          : apiOptions.retryDelay || 1000;

        setTimeout(() => {
          fetchData();
        }, delay);
        return;
      }

      setState({
        data: [],
        pagination: null,
        loading: false,
        error: apiError,
        correlationId: apiError.correlationId,
      });

      retryCountRef.current = 0;
      apiOptions.onError?.(apiError);
    }
  }, [endpoint, paginationParams, filters, apiOptions]);

  const nextPage = useCallback(() => {
    if (state.pagination?.has_next) {
      setPaginationParams((prev) => ({
        ...prev,
        page: prev.page + 1,
      }));
    }
  }, [state.pagination?.has_next]);

  const prevPage = useCallback(() => {
    if (state.pagination?.has_prev) {
      setPaginationParams((prev) => ({
        ...prev,
        page: prev.page - 1,
      }));
    }
  }, [state.pagination?.has_prev]);

  const goToPage = useCallback(
    (page: number) => {
      if (page >= 1 && page <= (state.pagination?.total_pages || 1)) {
        setPaginationParams((prev) => ({ ...prev, page }));
      }
    },
    [state.pagination?.total_pages],
  );

  const setPerPage = useCallback((per_page: number) => {
    setPaginationParams((prev) => ({
      ...prev,
      per_page,
      page: 1, // Reset to first page when changing page size
    }));
  }, []);

  const setSorting = useCallback((sort_by: string, sort_order: "asc" | "desc") => {
    setPaginationParams((prev) => ({
      ...prev,
      sort_by,
      sort_order,
      page: 1, // Reset to first page when changing sorting
    }));
  }, []);

  const reset = useCallback(() => {
    setState({
      data: [],
      pagination: null,
      loading: false,
      error: null,
    });
    setPaginationParams({
      page: initialPage,
      per_page: initialPerPage,
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    retryCountRef.current = 0;
  }, [initialPage, initialPerPage, sortBy, sortOrder]);

  useEffect(() => {
    if (apiOptions.immediate !== false) {
      fetchData();
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData]);

  return {
    ...state,
    nextPage,
    prevPage,
    goToPage,
    setPerPage,
    setSorting,
    refetch: fetchData,
    reset,
  };
}

/**
 * Hook for mutations (POST, PUT, PATCH, DELETE) with loading states
 */
export function useMutation<TData = any, TVariables = any>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: UseMutationOptions = {},
): UseMutationState<TData> & {
  mutate: (variables: TVariables) => Promise<void>;
  reset: () => void;
} {
  const [state, setState] = useState<UseMutationState<TData>>({
    data: null,
    loading: false,
    error: null,
  });

  const { onSuccess, onError } = options;

  const mutate = useCallback(
    async (variables: TVariables) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const result = await mutationFn(variables);

        setState({
          data: result,
          loading: false,
          error: null,
          correlationId: (result as any)?.correlation_id,
        });

        onSuccess?.(result);
      } catch (error) {
        const apiError = error as ApiClientError;

        setState({
          data: null,
          loading: false,
          error: apiError,
          correlationId: apiError.correlationId,
        });

        onError?.(apiError);
      }
    },
    [mutationFn, onSuccess, onError],
  );

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
    });
  }, []);

  return {
    ...state,
    mutate,
    reset,
  };
}

/**
 * Convenience hooks for common HTTP methods
 */
export function usePost<TData = any, TVariables = any>(
  endpoint: string,
  options: UseMutationOptions = {},
) {
  return useMutation<TData, TVariables>(
    (variables) => apiClient.post<TData>(endpoint, variables),
    options,
  );
}

export function usePut<TData = any, TVariables = any>(
  endpoint: string,
  options: UseMutationOptions = {},
) {
  return useMutation<TData, TVariables>(
    (variables) => apiClient.put<TData>(endpoint, variables),
    options,
  );
}

export function usePatch<TData = any, TVariables = any>(
  endpoint: string,
  options: UseMutationOptions = {},
) {
  return useMutation<TData, TVariables>(
    (variables) => apiClient.patch<TData>(endpoint, variables),
    options,
  );
}

export function useDelete<TData = any>(endpoint: string, options: UseMutationOptions = {}) {
  return useMutation<TData, void>(() => apiClient.delete<TData>(endpoint), options);
}

/**
 * Hook for handling API errors with user-friendly messages
 */
export function useApiErrorHandler() {
  const formatError = useCallback((error: ApiClientError): string => {
    if (error.isValidationError()) {
      const validationErrors = apiUtils.formatValidationErrors(error);
      return validationErrors.join(", ");
    }

    if (error.isAuthenticationError()) {
      return "Please log in to continue.";
    }

    if (error.isAuthorizationError()) {
      return "You do not have permission to perform this action.";
    }

    if (error.isNotFoundError()) {
      return "The requested resource was not found.";
    }

    if (error.isRateLimitError()) {
      const retryAfter = error.details?.retry_after;
      return retryAfter
        ? `Too many requests. Please try again in ${retryAfter} seconds.`
        : "Too many requests. Please try again later.";
    }

    if (error.isServerError()) {
      return "A server error occurred. Please try again later.";
    }

    return error.message || "An unexpected error occurred.";
  }, []);

  const shouldRetry = useCallback((error: ApiClientError): boolean => {
    return apiUtils.isRetryableError(error);
  }, []);

  const getRetryDelay = useCallback((error: ApiClientError): number => {
    return apiUtils.getRetryDelay(error);
  }, []);

  return {
    formatError,
    shouldRetry,
    getRetryDelay,
  };
}
