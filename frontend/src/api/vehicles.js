import { apiClient } from "./client";

/**
 * Vehicles API module for VoltSlot frontend.
 * Communicates with Django REST Framework backend endpoints:
 * - GET  /api/vehicles/ (List authenticated user's vehicles)
 * - POST /api/vehicles/ (Register new vehicle for authenticated user)
 *
 * NOTE: The backend only implements ListCreateAPIView for vehicles.
 * No PUT, PATCH, or DELETE endpoints exist in the backend contract.
 */

/**
 * Fetches the authenticated user's registered vehicles.
 * @param {string} token - DRF Auth Token
 * @returns {Promise<Array<{id: number, owner: number, registration_number: string, make: string, model: string, battery_capacity_kwh: string|null, created_at: string}>>}
 */
export async function fetchVehiclesApi(token) {
  if (!token) {
    throw new Error("Authentication token is required to fetch vehicles.");
  }
  const data = await apiClient("/api/vehicles/", { method: "GET" }, token);
  return Array.isArray(data) ? data : [];
}

/**
 * Registers a new vehicle for the authenticated user.
 * @param {object} vehicleData
 * @param {string} vehicleData.registration_number
 * @param {string} vehicleData.make
 * @param {string} vehicleData.model
 * @param {string|number|null} [vehicleData.battery_capacity_kwh]
 * @param {string} token - DRF Auth Token
 * @returns {Promise<{id: number, owner: number, registration_number: string, make: string, model: string, battery_capacity_kwh: string|null, created_at: string}>}
 */
export async function createVehicleApi(vehicleData, token) {
  if (!token) {
    throw new Error("Authentication token is required to register a vehicle.");
  }
  return apiClient(
    "/api/vehicles/",
    {
      method: "POST",
      body: vehicleData,
    },
    token
  );
}
