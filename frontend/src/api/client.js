/**
 * Centralized API Client for VoltSlot frontend.
 * Uses browser Fetch API to communicate with Django REST Framework backend.
 */

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

/**
 * Extracts a human-readable error message from DRF error payload.
 */
function formatDrfErrorMessage(data, status) {
  if (!data) {
    return `Request failed with status ${status}`;
  }
  if (typeof data === "string") {
    return data;
  }
  if (data.detail && typeof data.detail === "string") {
    return data.detail;
  }
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
    return data.non_field_errors.join(" ");
  }

  // Concatenate field-level errors (e.g. { email: ["Already exists"] })
  const fieldErrors = [];
  for (const [field, errors] of Object.entries(data)) {
    if (Array.isArray(errors)) {
      fieldErrors.push(`${field}: ${errors.join(" ")}`);
    } else if (typeof errors === "string") {
      fieldErrors.push(`${field}: ${errors}`);
    }
  }
  if (fieldErrors.length > 0) {
    return fieldErrors.join(" | ");
  }

  return `Request failed with status ${status}`;
}

/**
 * Base fetch wrapper.
 * @param {string} endpoint - e.g. '/api/auth/login/'
 * @param {object} options - fetch options
 * @param {string|null} token - DRF auth token
 */
export async function apiClient(endpoint, options = {}, token = null) {
  const url = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  const headers = {
    Accept: "application/json",
    ...options.headers,
  };

  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  if (token) {
    headers["Authorization"] = `Token ${token}`;
  }

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (networkError) {
    throw new ApiError(
      networkError.message || "Network error. Unable to connect to backend server.",
      0,
      null
    );
  }

  // Handle empty bodies (204 No Content, etc.)
  if (response.status === 204) {
    return null;
  }

  let responseData = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      responseData = await response.json();
    } catch {
      responseData = null;
    }
  } else {
    try {
      responseData = await response.text();
    } catch {
      responseData = null;
    }
  }

  if (!response.ok) {
    const errorMessage = formatDrfErrorMessage(responseData, response.status);
    throw new ApiError(errorMessage, response.status, responseData);
  }

  return responseData;
}
