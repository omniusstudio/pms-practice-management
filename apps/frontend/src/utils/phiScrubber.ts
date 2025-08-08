/**
 * PHI (Protected Health Information) scrubbing utility for frontend
 * Removes sensitive patient data from logs and error reports
 */

// Common PHI patterns to detect and scrub
const PHI_PATTERNS = [
  // Social Security Numbers
  { pattern: /\b\d{3}-\d{2}-\d{4}\b/g, replacement: "[SSN-REDACTED]" },
  { pattern: /\b\d{9}\b/g, replacement: "[SSN-REDACTED]" },

  // Phone numbers
  { pattern: /\b\d{3}-\d{3}-\d{4}\b/g, replacement: "[PHONE-REDACTED]" },
  { pattern: /\(\d{3}\)\s*\d{3}-\d{4}/g, replacement: "[PHONE-REDACTED]" },
  { pattern: /\b\d{10}\b/g, replacement: "[PHONE-REDACTED]" },

  // Email addresses
  {
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    replacement: "[EMAIL-REDACTED]",
  },

  // Date of birth patterns
  { pattern: /\b\d{1,2}\/\d{1,2}\/\d{4}\b/g, replacement: "[DOB-REDACTED]" },
  { pattern: /\b\d{4}-\d{2}-\d{2}\b/g, replacement: "[DOB-REDACTED]" },
  { pattern: /\b\d{2}-\d{2}-\d{4}\b/g, replacement: "[DOB-REDACTED]" },

  // Medical record numbers
  { pattern: /\bMRN[:\s]*\d+/gi, replacement: "[MRN-REDACTED]" },
  { pattern: /\bMedical Record[:\s]*\d+/gi, replacement: "[MRN-REDACTED]" },
  { pattern: /\bRecord Number[:\s]*\d+/gi, replacement: "[MRN-REDACTED]" },

  // Patient identifiers
  { pattern: /\bPatient ID[:\s]*\d+/gi, replacement: "[PATIENT-ID-REDACTED]" },
  { pattern: /\bPatient[:\s]+[A-Za-z]+\s+[A-Za-z]+/gi, replacement: "[PATIENT-NAME-REDACTED]" },

  // Insurance information
  { pattern: /\bPolicy[:\s]*\d+/gi, replacement: "[POLICY-REDACTED]" },
  { pattern: /\bInsurance[:\s]*\d+/gi, replacement: "[INSURANCE-REDACTED]" },

  // Address patterns (basic)
  {
    pattern:
      /\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b/gi,
    replacement: "[ADDRESS-REDACTED]",
  },

  // ZIP codes
  { pattern: /\b\d{5}(-\d{4})?\b/g, replacement: "[ZIP-REDACTED]" },

  // Credit card numbers (basic pattern)
  { pattern: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, replacement: "[CARD-REDACTED]" },

  // Common PHI field patterns
  { pattern: /\bDOB[:\s]+\d{1,2}\/\d{1,2}\/\d{4}/gi, replacement: "[DOB-REDACTED]" },
  { pattern: /\bSSN[:\s]+\d{3}-\d{2}-\d{4}/gi, replacement: "[SSN-REDACTED]" },
  { pattern: /\bPhone[:\s]+\d{3}-\d{3}-\d{4}/gi, replacement: "[PHONE-REDACTED]" },
];

// Sensitive field names that should be completely redacted
const SENSITIVE_FIELDS = [
  "ssn",
  "social_security_number",
  "socialSecurityNumber",
  "dob",
  "date_of_birth",
  "dateOfBirth",
  "birthDate",
  "phone",
  "phoneNumber",
  "phone_number",
  "mobile",
  "email",
  "emailAddress",
  "email_address",
  "address",
  "street_address",
  "streetAddress",
  "zip",
  "zipCode",
  "zip_code",
  "postal_code",
  "postalCode",
  "mrn",
  "medical_record_number",
  "medicalRecordNumber",
  "patient_id",
  "patientId",
  "patient_name",
  "patientName",
  "first_name",
  "firstName",
  "last_name",
  "lastName",
  "insurance",
  "policy_number",
  "policyNumber",
  "credit_card",
  "creditCard",
  "card_number",
  "cardNumber",
];

/**
 * Scrub PHI from a string
 */
export function scrubPHI(input: string): string {
  if (typeof input !== "string") {
    return input;
  }

  let scrubbed = input;

  // Apply all PHI patterns
  PHI_PATTERNS.forEach(({ pattern, replacement }) => {
    scrubbed = scrubbed.replace(pattern, replacement);
  });

  return scrubbed;
}

/**
 * Scrub PHI from an object (recursive)
 */
export function scrubPHIFromObject(obj: any): any {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (typeof obj === "string") {
    return scrubPHI(obj);
  }

  if (typeof obj === "number" || typeof obj === "boolean") {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => scrubPHIFromObject(item));
  }

  if (typeof obj === "object") {
    const scrubbed: any = {};

    Object.keys(obj).forEach((key) => {
      const lowerKey = key.toLowerCase();

      // Check if field name indicates sensitive data
      if (SENSITIVE_FIELDS.some((field) => lowerKey.includes(field))) {
        scrubbed[key] = "[REDACTED]";
      } else {
        scrubbed[key] = scrubPHIFromObject(obj[key]);
      }
    });

    return scrubbed;
  }

  return obj;
}

/**
 * Scrub PHI from JSON string
 */
export function scrubPHIFromJSON(jsonString: string): string {
  try {
    const parsed = JSON.parse(jsonString);
    const scrubbed = scrubPHIFromObject(parsed);
    return JSON.stringify(scrubbed);
  } catch (error) {
    // If not valid JSON, treat as regular string
    return scrubPHI(jsonString);
  }
}

/**
 * Scrub PHI from URL parameters
 */
export function scrubPHIFromURL(url: string): string {
  try {
    const urlObj = new URL(url);

    // Scrub search parameters
    const params = new URLSearchParams(urlObj.search);
    const scrubbedParams = new URLSearchParams();

    params.forEach((value, key) => {
      const lowerKey = key.toLowerCase();

      if (SENSITIVE_FIELDS.some((field) => lowerKey.includes(field))) {
        scrubbedParams.set(key, "[REDACTED]");
      } else {
        scrubbedParams.set(key, scrubPHI(value));
      }
    });

    urlObj.search = scrubbedParams.toString();

    // Scrub pathname if it contains sensitive data
    urlObj.pathname = scrubPHI(urlObj.pathname);

    return urlObj.toString();
  } catch (error) {
    // If not a valid URL, treat as regular string
    return scrubPHI(url);
  }
}

/**
 * Scrub PHI from form data
 */
export function scrubPHIFromFormData(formData: FormData): FormData {
  const scrubbed = new FormData();

  formData.forEach((value, key) => {
    const lowerKey = key.toLowerCase();

    if (SENSITIVE_FIELDS.some((field) => lowerKey.includes(field))) {
      scrubbed.set(key, "[REDACTED]");
    } else if (typeof value === "string") {
      scrubbed.set(key, scrubPHI(value));
    } else {
      scrubbed.set(key, value);
    }
  });

  return scrubbed;
}

/**
 * Check if a string contains potential PHI
 */
export function containsPHI(input: string): boolean {
  if (typeof input !== "string") {
    return false;
  }

  return PHI_PATTERNS.some(({ pattern }) => pattern.test(input));
}

/**
 * Anonymize user ID for logging
 */
export function anonymizeUserId(userId: string): string {
  if (!userId) {
    return "anonymous";
  }

  // Create a simple hash for anonymization
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    const char = userId.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }

  const anonymized = Math.abs(hash) % 10000;
  return `user_${anonymized.toString().padStart(4, "0")}`;
}

/**
 * Create a test string with PHI for validation
 */
export function createPHITestString(): string {
  return (
    "Test patient data: John Doe, SSN: 123-45-6789, " +
    "DOB: 01/15/1980, Phone: (555) 123-4567, " +
    "Email: john.doe@email.com, MRN: 12345, " +
    "Address: 123 Main Street, ZIP: 12345"
  );
}

/**
 * Validate PHI scrubbing by testing with sample data
 */
export function validatePHIScrubbing(): boolean {
  const testString = createPHITestString();
  const scrubbed = scrubPHI(testString);

  // Check that no PHI patterns remain
  const stillContainsPHI = PHI_PATTERNS.some(({ pattern }) => {
    // Reset regex lastIndex to avoid issues with global flags
    pattern.lastIndex = 0;
    return pattern.test(scrubbed);
  });

  return !stillContainsPHI;
}
