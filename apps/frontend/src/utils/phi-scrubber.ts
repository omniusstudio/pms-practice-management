/**
 * Frontend PHI scrubbing utilities for HIPAA-compliant logging.
 */

// PHI patterns to detect and scrub from logs
const PHI_PATTERNS: Array<[RegExp, string]> = [
  // Social Security Numbers
  [/\b\d{3}-\d{2}-\d{4}\b/g, "[SSN-REDACTED]"],
  [/\b\d{9}\b/g, "[SSN-REDACTED]"],

  // Email addresses
  [/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/gi, "[EMAIL-REDACTED]"],

  // Phone numbers
  [/\b\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b/g, "[PHONE-REDACTED]"],

  // Credit card numbers (basic pattern)
  [/\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g, "[CARD-REDACTED]"],

  // Medical record numbers
  [/\bMRN[-:\s]*\d+\b/gi, "[MRN-REDACTED]"],
  [/\bMR[-:\s]*\d+\b/gi, "[MRN-REDACTED]"],

  // Date of birth patterns
  [/\b\d{1,2}\/\d{1,2}\/\d{4}\b/g, "[DOB-REDACTED]"],
  [/\b\d{4}-\d{2}-\d{2}\b/g, "[DOB-REDACTED]"],

  // Insurance numbers
  [/\bINS[-:\s]*[A-Z0-9]+\b/gi, "[INSURANCE-REDACTED]"],

  // Common name patterns (when in specific contexts)
  [/\bpatient[-_\s]+name[-:\s]*[A-Za-z\s]+\b/gi, "[PATIENT-NAME-REDACTED]"],
  [/\bfirst[-_\s]+name[-:\s]*[A-Za-z]+\b/gi, "[FIRST-NAME-REDACTED]"],
  [/\blast[-_\s]+name[-:\s]*[A-Za-z]+\b/gi, "[LAST-NAME-REDACTED]"],
];

// Sensitive field names that should be scrubbed
const SENSITIVE_FIELDS = new Set([
  "ssn",
  "social_security_number",
  "social_security",
  "email",
  "email_address",
  "phone",
  "phone_number",
  "telephone",
  "first_name",
  "last_name",
  "full_name",
  "name",
  "date_of_birth",
  "dob",
  "birth_date",
  "address",
  "street_address",
  "home_address",
  "medical_record_number",
  "mrn",
  "patient_id",
  "insurance_number",
  "policy_number",
  "diagnosis",
  "medical_condition",
  "treatment",
  "prescription",
  "medication",
  "password",
  "token",
  "secret",
  "key",
]);

/**
 * Scrub PHI patterns from a string
 */
export function scrubPHIFromString(text: string): string {
  if (typeof text !== "string") {
    return text;
  }

  let scrubbed = text;

  // Apply all PHI patterns
  for (const [pattern, replacement] of PHI_PATTERNS) {
    scrubbed = scrubbed.replace(pattern, replacement);
  }

  return scrubbed;
}

/**
 * Recursively scrub PHI from object data
 */
export function scrubPHIFromObject(data: Record<string, any>): Record<string, any> {
  if (typeof data !== "object" || data === null) {
    return data;
  }

  if (Array.isArray(data)) {
    return data.map((item) => scrubPHI(item));
  }

  const scrubbed: Record<string, any> = {};

  for (const [key, value] of Object.entries(data)) {
    // Check if field name indicates sensitive data
    if (SENSITIVE_FIELDS.has(key.toLowerCase())) {
      scrubbed[key] = "[REDACTED]";
    } else {
      scrubbed[key] = scrubPHI(value);
    }
  }

  return scrubbed;
}

/**
 * Main PHI scrubbing function that handles various data types
 */
export function scrubPHI(data: any): any {
  if (typeof data === "string") {
    return scrubPHIFromString(data);
  } else if (typeof data === "object" && data !== null) {
    return scrubPHIFromObject(data);
  } else {
    return data;
  }
}

/**
 * Scrub PHI from URL parameters and paths
 */
export function scrubPHIFromURL(url: string): string {
  if (typeof url !== "string") {
    return url;
  }

  // Scrub query parameters that might contain PHI
  let scrubbed = url;

  // Common PHI parameter patterns
  const phiParams = [
    /([?&])(email|ssn|phone|name|dob|mrn)=([^&]*)/gi,
    /([?&])(patient_id|user_id)=([^&]*)/gi,
  ];

  for (const pattern of phiParams) {
    scrubbed = scrubbed.replace(pattern, "$1$2=[REDACTED]");
  }

  // Apply general PHI patterns to the URL
  scrubbed = scrubPHIFromString(scrubbed);

  return scrubbed;
}
