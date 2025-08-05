/**
 * Tests for frontend metrics collection utilities.
 */

import {
  metrics,
  recordPerformance,
  recordError,
  recordUserAction,
  recordPageLoad,
  recordApiCall,
  setMetricsEnabled,
} from '../metrics';
import { Logger } from '../logger';

import { vi } from 'vitest';

// Mock the Logger methods
vi.spyOn(Logger, 'info').mockImplementation(() => {});
vi.spyOn(Logger, 'warn').mockImplementation(() => {});
vi.spyOn(Logger, 'error').mockImplementation(() => {});

// Mock fetch
global.fetch = vi.fn();

// Mock performance API
Object.defineProperty(window, 'performance', {
  value: {
    now: vi.fn(() => Date.now()),
    getEntriesByType: vi.fn((type) => {
      if (type === 'navigation') {
        return [{
          fetchStart: 100,
          loadEventEnd: 1600,
          domContentLoadedEventEnd: 1100,
          responseEnd: 600,
        }];
      }
      return [];
    }),
    mark: vi.fn(),
    measure: vi.fn(),
    navigation: {
      type: 'navigate',
    },
    timing: {
      navigationStart: Date.now() - 1000,
      loadEventEnd: Date.now(),
      domContentLoadedEventEnd: Date.now() - 500,
    },
  },
  writable: true,
});

// Mock PerformanceObserver
global.PerformanceObserver = vi.fn().mockImplementation((_callback) => ({
  observe: vi.fn(),
  disconnect: vi.fn(),
  takeRecords: vi.fn(() => []),
})) as any;

// Add supportedEntryTypes property
(global.PerformanceObserver as any).supportedEntryTypes = [
  'navigation',
  'paint',
  'largest-contentful-paint',
  'first-input',
  'layout-shift',
];

describe('Frontend Metrics', () => {
  const mockFetch = fetch as any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response);
    
    // Clear the metrics buffer
    (metrics as any).metricsBuffer = [];
    setMetricsEnabled(true);
  });

  describe('Performance Metrics', () => {
    it('should record performance metrics', () => {
      recordPerformance('page_load', 1500, { page: '/dashboard' });
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
      expect(metricsBuffer[0]).toMatchObject({
        name: 'page_load',
        value: 1500,
        tags: expect.objectContaining({
          page: '/dashboard',
        }),
      });
    });

    it('should record page load metrics', () => {
      recordPageLoad('/dashboard');
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(3); // page_load_time, dom_content_loaded, first_paint
      expect(metricsBuffer[0]).toMatchObject({
        name: 'page_load_time',
        value: 1500, // loadEventEnd (1600) - fetchStart (100)
        tags: expect.objectContaining({
          page: '/dashboard',
          type: 'page_load',
        }),
      });
    });

    it('should record API call metrics', () => {
      recordApiCall('GET', '/api/patients', 200, 750, true);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
      expect(metricsBuffer[0]).toMatchObject({
        name: 'api_call_duration',
        value: 750,
        tags: expect.objectContaining({
          method: 'GET',
          url: '/api/patients',
          status: '200',
        }),
      });
    });
  });

  describe('Error Metrics', () => {
    it('should record JavaScript errors', () => {
      const error = new Error('Test error');
      recordError('javascript_error', error, 'PatientForm');
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
      expect(metricsBuffer[0]).toMatchObject({
        name: 'javascript_error',
        error: 'Test error',
        component: 'PatientForm',
      });
    });

    it('should record string errors', () => {
      recordError('api_error', 'Network timeout', 'ApiService');
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
      expect(metricsBuffer[0]).toMatchObject({
        name: 'api_error',
        error: 'Network timeout',
        component: 'ApiService',
      });
    });
  });

  describe('User Action Metrics', () => {
    it('should record user actions', () => {
      recordUserAction('button_click', 'PatientForm', true, 100);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
      expect(metricsBuffer[0]).toMatchObject({
        action: 'button_click',
        component: 'PatientForm',
        success: true,
        duration: 100,
      });
    });

    it('should record failed user actions', () => {
      recordUserAction('form_submit', 'PatientForm', false);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
      expect(metricsBuffer[0]).toMatchObject({
        action: 'form_submit',
        component: 'PatientForm',
        success: false,
      });
    });
  });

  describe('Metrics Control', () => {
    it('should disable metrics collection', () => {
      setMetricsEnabled(false);
      
      recordPerformance('test_metric', 100);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(0);
    });

    it('should enable metrics collection', () => {
      setMetricsEnabled(false);
      setMetricsEnabled(true);
      
      recordPerformance('test_metric', 100);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
    });
  });

  describe('Buffer Management', () => {
    it('should add metrics to buffer', () => {
      recordPerformance('metric1', 100);
      recordPerformance('metric2', 200);
      recordPerformance('metric3', 300);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(3);
    });

    it('should flush metrics when buffer is full', async () => {
      // Set a small buffer size for testing
      (metrics as any).maxBufferSize = 2;
      
      recordPerformance('metric1', 100);
      recordPerformance('metric2', 200);
      
      // Adding third metric should trigger flush
      recordPerformance('metric3', 300);
      
      // Give some time for async flush
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockFetch).toHaveBeenCalled();
    });
  });

  describe('HIPAA Compliance', () => {
    it('should not expose PHI in metrics', () => {
      // Record metrics that might contain PHI
      recordError('validation_error', 'Invalid email: john@example.com');
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer[0].error).not.toContain('john@example.com');
    });

    it('should scrub sensitive data from tags', () => {
      recordPerformance('api_call', 100, {
        endpoint: '/api/patients/john@example.com',
      });
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      const tags = metricsBuffer[0].tags;
      expect(tags?.endpoint).not.toContain('john@example.com');
    });
  });

  describe('Error Handling', () => {
    it('should handle flush errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      recordPerformance('test_metric', 100);
      
      // Manually trigger flush
      await (metrics as any).flush();
      
      expect(Logger.error).toHaveBeenCalledWith(
        'Failed to send metrics to backend',
        expect.any(Error),
        expect.objectContaining({
          correlationId: expect.any(String),
        })
      );
    });

    it('should continue collecting metrics after flush error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      recordPerformance('test_metric1', 100);
      await (metrics as any).flush();
      
      // Should still be able to record new metrics
      recordPerformance('test_metric2', 200);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer.length).toBe(1);
      expect(metricsBuffer[0].name).toBe('test_metric2');
    });
  });

  describe('Timestamp and Correlation', () => {
    it('should add timestamps to metrics', () => {
      recordPerformance('test_metric', 100);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer[0]).toHaveProperty('timestamp');
      expect(typeof metricsBuffer[0].timestamp).toBe('number');
    });

    it('should preserve correlation IDs when available', () => {
      // Mock correlation ID in global context
      (global as any).correlationId = 'test-correlation-id';
      
      recordPerformance('test_metric', 100);
      
      const metricsBuffer = (metrics as any).metricsBuffer;
      expect(metricsBuffer[0]).toHaveProperty('correlationId');
      
      // Clean up
      delete (global as any).correlationId;
    });
  });
});