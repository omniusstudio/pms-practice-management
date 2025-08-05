/**
 * Tests for useMetrics React hooks.
 */

import { renderHook, act } from '@testing-library/react';
import { vi } from 'vitest';
import { useMetrics, usePageMetrics, useFormMetrics, useApiMetrics } from '../useMetrics';
import { metrics } from '../../utils/metrics';

// Spy on the metrics object methods
const mockRecordPerformance = vi.spyOn(metrics, 'recordPerformance').mockImplementation(() => {});
const mockRecordError = vi.spyOn(metrics, 'recordError').mockImplementation(() => {});
const mockRecordUserAction = vi.spyOn(metrics, 'recordUserAction').mockImplementation(() => {});
const mockRecordPageLoad = vi.spyOn(metrics, 'recordPageLoad').mockImplementation(() => {});
const mockRecordApiCall = vi.spyOn(metrics, 'recordApiCall').mockImplementation(() => {});

// Mock performance.now
Object.defineProperty(window, 'performance', {
  value: {
    now: vi.fn(() => Date.now()),
  },
  writable: true,
});

describe('useMetrics Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRecordPerformance.mockClear();
    mockRecordError.mockClear();
    mockRecordUserAction.mockClear();
    mockRecordPageLoad.mockClear();
    mockRecordApiCall.mockClear();
    (window.performance.now as any).mockReturnValue(1000);
  });

  it('should track component mount and unmount', () => {
    const { unmount } = renderHook(() => 
      useMetrics({ componentName: 'TestComponent' })
    );

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'component_mount',
      'TestComponent',
      true,
      undefined,
      expect.objectContaining({
        timestamp: expect.any(String),
      })
    );

    unmount();

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'component_unmount',
      'TestComponent',
      true,
      expect.any(Number),
      expect.objectContaining({
        lifetime: expect.any(String),
      })
    );
  });

  it('should provide trackAction function', () => {
    const { result } = renderHook(() => 
      useMetrics({ componentName: 'TestComponent' })
    );

    act(() => {
      result.current.trackAction('button_click', true, undefined, { button: 'save' });
    });

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'button_click',
      'TestComponent',
      true,
      undefined,
      expect.objectContaining({
        button: 'save',
        component: 'TestComponent',
      })
    );
  });

  it('should provide trackError function', () => {
    const { result } = renderHook(() => 
      useMetrics({ componentName: 'TestComponent' })
    );
    const error = new Error('Test error');

    act(() => {
      result.current.trackError(error, { context: 'validation' });
    });

    expect(mockRecordError).toHaveBeenCalledWith(
      'component_error',
      error,
      'TestComponent',
      expect.objectContaining({
        context: 'validation',
        component: 'TestComponent',
      })
    );
  });

  it('should provide trackPerformance function', () => {
    const { result } = renderHook(() => 
      useMetrics({ componentName: 'TestComponent' })
    );

    act(() => {
      result.current.trackPerformance('data_load', 500, { endpoint: '/api/data' });
    });

    expect(mockRecordPerformance).toHaveBeenCalledWith(
      'data_load',
      500,
      expect.objectContaining({
        endpoint: '/api/data',
        component: 'TestComponent',
      })
    );
  });

  it('should provide startTimer function', () => {
    const { result } = renderHook(() => 
      useMetrics({ componentName: 'TestComponent' })
    );

    let endTimer: () => number;
    act(() => {
      endTimer = result.current.startTimer('operation_timer');
    });

    let duration = 0;
    act(() => {
      duration = endTimer();
    });

    expect(typeof duration).toBe('number');
    expect(mockRecordPerformance).toHaveBeenCalledWith(
      'operation_timer',
      expect.any(Number),
      expect.objectContaining({
        type: 'timer',
        component: 'TestComponent',
      })
    );
  });

  it('should provide trackAsyncAction function', async () => {
    const { result } = renderHook(() => 
      useMetrics({ componentName: 'TestComponent' })
    );
    const asyncOperation = vi.fn().mockResolvedValue('success');

    let operationResult;
    await act(async () => {
      operationResult = await result.current.trackAsyncAction(
        'api_call',
        asyncOperation(),
        { endpoint: '/api/test' }
      );
    });

    expect(asyncOperation).toHaveBeenCalled();
    expect(operationResult).toBe('success');
    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'api_call',
      'TestComponent',
      true,
      expect.any(Number),
      expect.objectContaining({
        endpoint: '/api/test',
        component: 'TestComponent',
        async: 'true',
      })
    );
  });
});

describe('usePageMetrics Hook', () => {
  // Use the global mock

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should track page load on mount', () => {
    // Use the already mocked metrics
    
    renderHook(() => usePageMetrics('/dashboard'));

    // Fast-forward the timer
    act(() => {
      vi.advanceTimersByTime(150);
    });

    expect(mockRecordPageLoad).toHaveBeenCalledWith('/dashboard');
  });

  it('should track component mount for page', () => {
    renderHook(() => usePageMetrics('/dashboard'));

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'component_mount',
      'page_/dashboard',
      true,
      undefined,
      expect.objectContaining({
        timestamp: expect.any(String),
      })
    );
  });
});

describe('useFormMetrics Hook', () => {
  // Use the global mocks

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should track field interactions', () => {
    const { result } = renderHook(() => useFormMetrics('patient_form'));

    act(() => {
      result.current.trackFieldInteraction('email', 'focus');
    });

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'field_focus',
      'form_patient_form',
      true,
      undefined,
      expect.objectContaining({
        field: 'email',
        form: 'patient_form',
      })
    );
  });

  it('should track successful form submission', () => {
    const { result } = renderHook(() => useFormMetrics('patient_form'));

    act(() => {
      result.current.trackFormSubmission(true);
    });

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'form_submit',
      'form_patient_form',
      true,
      undefined,
      expect.objectContaining({
        form: 'patient_form',
        validation_errors: '0',
      })
    );
  });

  it('should track form submission with validation errors', () => {
    const { result } = renderHook(() => useFormMetrics('patient_form'));
    const validationErrors = ['Email is required', 'Phone is invalid'];

    act(() => {
      result.current.trackFormSubmission(false, validationErrors);
    });

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'form_submit',
      'form_patient_form',
      false,
      undefined,
      expect.objectContaining({
        form: 'patient_form',
        validation_errors: '2',
      })
    );

    expect(mockRecordError).toHaveBeenCalledWith(
      'component_error',
      'Form validation failed: Email is required, Phone is invalid',
      'form_patient_form',
      expect.objectContaining({
        form: 'patient_form',
        error_count: '2',
        component: 'form_patient_form',
      })
    );
  });

  it('should track form reset', () => {
    const { result } = renderHook(() => useFormMetrics('patient_form'));

    act(() => {
      result.current.trackFormReset();
    });

    expect(mockRecordUserAction).toHaveBeenCalledWith(
      'form_reset',
      'form_patient_form',
      true,
      undefined,
      expect.objectContaining({
        form: 'patient_form',
      })
    );
  });
});

describe('useApiMetrics Hook', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    (window.performance.now as any)
      .mockReturnValueOnce(1000) // Start time
      .mockReturnValueOnce(1500); // End time
  });

  it('should track successful API calls', async () => {
    const { result } = renderHook(() => useApiMetrics());
    const mockApiCall = vi.fn().mockResolvedValue({ data: 'success' });
    // Use the already mocked metrics

    let apiResult;
    await act(async () => {
      apiResult = await result.current.trackApiCall(
        'GET',
        '/api/patients',
        mockApiCall
      );
    });

    expect(mockApiCall).toHaveBeenCalled();
    expect(apiResult).toEqual({ data: 'success' });
    expect(mockRecordApiCall).toHaveBeenCalledWith(
      'GET',
      '/api/patients',
      200,
      expect.any(Number),
      true
    );
  });

  it('should track failed API calls', async () => {
    const { result } = renderHook(() => useApiMetrics());
    const error = { response: { status: 404 } };
    const mockApiCall = vi.fn().mockRejectedValue(error);
    // Use the already mocked metrics

    await act(async () => {
      try {
        await result.current.trackApiCall('GET', '/api/patients/123', mockApiCall);
      } catch (e) {
        // Expected to throw
      }
    });

    expect(mockRecordApiCall).toHaveBeenCalledWith(
      'GET',
      '/api/patients/123',
      404,
      expect.any(Number),
      false
    );
  });

  it('should handle API calls without response status', async () => {
    const { result } = renderHook(() => useApiMetrics());
    const error = new Error('Network error');
    const mockApiCall = vi.fn().mockRejectedValue(error);

    await act(async () => {
      try {
        await result.current.trackApiCall('POST', '/api/patients', mockApiCall);
      } catch (e) {
        // Expected to throw
      }
    });

    expect(mockRecordApiCall).toHaveBeenCalledWith(
      'POST',
      '/api/patients',
      500, // Default error status
      expect.any(Number),
      false
    );
  });
});