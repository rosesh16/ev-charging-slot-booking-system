import { apiClient } from "./client";

/**
 * Bookings API module for VoltSlot frontend.
 * Communicates with Django REST Framework backend endpoints:
 * - GET  /api/bookings/             (List user's bookings)
 * - POST /api/bookings/             (Create a 30-minute booking)
 * - GET  /api/bookings/<id>/        (Retrieve single booking)
 * - POST /api/bookings/<id>/cancel/ (Cancel an active booking)
 */

/**
 * Fetches the authenticated user's booking history.
 * @param {string} token - DRF Auth Token
 * @returns {Promise<Array<object>>}
 */
export async function fetchBookingsApi(token) {
  if (!token) {
    throw new Error("Authentication token is required to fetch bookings.");
  }
  const data = await apiClient("/api/bookings/", { method: "GET" }, token);
  return Array.isArray(data) ? data : [];
}

/**
 * Fetches details for a specific booking.
 * @param {number|string} bookingId
 * @param {string} token - DRF Auth Token
 * @returns {Promise<object>}
 */
export async function fetchBookingDetailApi(bookingId, token) {
  if (!token) {
    throw new Error("Authentication token is required to fetch booking details.");
  }
  return apiClient(`/api/bookings/${bookingId}/`, { method: "GET" }, token);
}

/**
 * Creates a new booking reservation.
 * The backend enforces:
 *  - exactly 30 minutes duration
 *  - future start time
 *  - vehicle owned by authenticated user
 *  - charger and station active, and charger not OFFLINE or MAINTENANCE
 *  - no conflicting active booking on the same charger (returns 409 Conflict if booked)
 *
 * @param {object} bookingData
 * @param {number} bookingData.charger - Charger ID
 * @param {number} bookingData.vehicle - Vehicle ID
 * @param {string} bookingData.start_time - ISO 8601 string
 * @param {string} bookingData.end_time - ISO 8601 string
 * @param {string} token - DRF Auth Token
 * @returns {Promise<object>}
 */
export async function createBookingApi(bookingData, token) {
  if (!token) {
    throw new Error("Authentication token is required to reserve a booking.");
  }
  return apiClient(
    "/api/bookings/",
    {
      method: "POST",
      body: bookingData,
    },
    token
  );
}

/**
 * Cancels an active booking for the authenticated user.
 * Backend only permits cancelling CONFIRMED bookings that have not yet started.
 *
 * @param {number|string} bookingId
 * @param {string} token - DRF Auth Token
 * @returns {Promise<object>} Updated booking object
 */
export async function cancelBookingApi(bookingId, token) {
  if (!token) {
    throw new Error("Authentication token is required to cancel a booking.");
  }
  return apiClient(
    `/api/bookings/${bookingId}/cancel/`,
    {
      method: "POST",
    },
    token
  );
}
