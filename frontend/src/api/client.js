import axios from 'axios';

// Same-origin `/api` in development (proxied by Vite to Django); the hosted API URL in production.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const client = axios.create({ baseURL: API_BASE_URL, timeout: 90_000 });

/**
 * Normalise an axios error into { message, fields } so forms can show
 * DRF's field-keyed validation errors under the right inputs.
 */
export function parseApiError(error) {
  const data = error?.response?.data;
  if (data && typeof data === 'object') {
    const fields = {};
    let message = data.detail || null;
    for (const [key, value] of Object.entries(data)) {
      const text = Array.isArray(value) ? value.join(' ') : String(value);
      if (key === 'detail') continue;
      if (key === 'non_field_errors') message = text;
      else fields[key] = text;
    }
    if (!message && Object.keys(fields).length) message = 'Please fix the highlighted fields.';
    return { message: message || 'Request failed.', fields };
  }
  if (error?.code === 'ECONNABORTED') return { message: 'The API took too long to respond. Please try again.', fields: {} };
  return { message: error?.message || 'Network error — is the API running?', fields: {} };
}

export default client;
