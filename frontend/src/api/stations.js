import { apiClient } from "./client";

/**
 * Station and Charger API module for VoltSlot frontend.
 * Communicates with Django REST Framework backend endpoints:
 * - GET /api/stations/
 * - GET /api/stations/<id>/
 * - GET /api/chargers/
 * - GET /api/chargers/?station=<id>
 * - GET /api/chargers/<charger_id>/availability/?start=<ISO>&end=<ISO>
 */

/**
 * Fetches all active stations.
 * @returns {Promise<Array<{id: number, name: string, address: string, city: string, latitude: string|null, longitude: string|null, is_active: boolean, created_at: string}>>}
 */
export async function fetchStationsApi() {
  const data = await apiClient("/api/stations/");
  return Array.isArray(data) ? data : [];
}

/**
 * Fetches single station with active chargers.
 * @param {number|string} stationId
 */
export async function fetchStationDetailApi(stationId) {
  return apiClient(`/api/stations/${stationId}/`);
}

/**
 * Fetches all active chargers, optionally filtered by station.
 * @param {number|string|null} stationId
 * @returns {Promise<Array<{id: number, name: string, connector_type: string, power_kw: string, status: string, is_active: boolean, station: {id: number, name: string, address: string, city: string}}>>}
 */
export async function fetchChargersApi(stationId = null) {
  const endpoint = stationId ? `/api/chargers/?station=${stationId}` : "/api/chargers/";
  const data = await apiClient(endpoint);
  return Array.isArray(data) ? data : [];
}

/**
 * Fetches stations with their installed chargers attached.
 * Performs two parallel queries (stations and chargers) and groups them locally.
 * Avoids N+1 query requests while keeping data strictly synchronized.
 */
export async function fetchStationsWithChargers() {
  const [stations, chargers] = await Promise.all([
    fetchStationsApi(),
    fetchChargersApi(),
  ]);

  const chargersByStation = {};
  for (const ch of chargers) {
    const stId = ch.station ? ch.station.id : null;
    if (stId) {
      if (!chargersByStation[stId]) {
        chargersByStation[stId] = [];
      }
      chargersByStation[stId].push(ch);
    }
  }

  return stations.map((st) => {
    const stationChargers = chargersByStation[st.id] || [];
    const totalChargers = stationChargers.length;
    const availableChargers = stationChargers.filter((c) => c.status === "AVAILABLE").length;

    return {
      ...st,
      chargers: stationChargers,
      totalChargers,
      availableChargers,
      isLive: true,
    };
  });
}

/**
 * Queries Phase 3B charger availability endpoint for existing booked intervals.
 * @param {number|string} chargerId
 * @param {string} startIso - Timezone-aware ISO 8601 string
 * @param {string} endIso - Timezone-aware ISO 8601 string
 * @returns {Promise<{charger_id: number, start: string, end: string, slot_duration_minutes: number, booked_intervals: Array<{start_time: string, end_time: string}>}>}
 */
export async function fetchChargerAvailabilityApi(chargerId, startIso, endIso) {
  const query = new URLSearchParams({
    start: startIso,
    end: endIso,
  }).toString();

  return apiClient(`/api/chargers/${chargerId}/availability/?${query}`);
}
