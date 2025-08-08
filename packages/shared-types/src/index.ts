// Shared TypeScript types for Mental Health PMS
// HIPAA-compliant type definitions

// Base types
export interface BaseEntity {
  id: string;
  createdAt: Date;
  updatedAt: Date;
}

// User and Authentication types
export interface User extends BaseEntity {
  email: string;
  role: UserRole;
  isActive: boolean;
  lastLoginAt?: Date;
}

export enum UserRole {
  ADMIN = 'admin',
  CLINICIAN = 'clinician',
  STAFF = 'staff',
  PATIENT = 'patient',
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: PaginationMeta;
}

// Error types
export interface ApiError {
  error: string;
  message: string;
  correlation_id: string;
  details?: Record<string, any>;
}

// Specific error types
export interface ValidationErrorDetails {
  field_errors: Record<string, string[]>;
}

export interface AuthorizationErrorDetails {
  required_role?: string;
  error_code?: string;
}

export interface RateLimitErrorDetails {
  retry_after_seconds?: number;
}

export interface ServiceErrorDetails {
  retry_after_seconds?: number;
}

// Audit types (HIPAA compliance)
export interface AuditLog extends BaseEntity {
  userId: string;
  action: string;
  resource: string;
  resourceId?: string;
  ipAddress: string;
  userAgent: string;
  correlationId: string;
}

// Configuration types
export interface AppConfig {
  apiUrl: string;
  environment: 'development' | 'staging' | 'production';
  features: FeatureFlags;
}

export interface FeatureFlags {
  [key: string]: boolean;
}

// Form validation types
export interface ValidationError {
  field: string;
  message: string;
}

export interface FormState<T> {
  data: T;
  errors: ValidationError[];
  isSubmitting: boolean;
  isValid: boolean;
}
