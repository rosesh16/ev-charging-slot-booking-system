/**
 * Illustrative Mock Data for VoltSlot UI (Phase 3C Step 2).
 * NOTE: All data below is illustrative mock data for layout prototyping.
 * Real-time data will be retrieved from the Django REST Framework API in future integration steps.
 */

export const MOCK_SUMMARY_METRICS = {
  isMockData: true,
  nearbyStationsCount: 4,
  activeChargersCount: 18,
  registeredVehiclesCount: 2,
  upcomingBookingsCount: 1,
};

export const MOCK_STATIONS = [
  {
    id: 1,
    isMockData: true,
    name: "Downtown Supercharge Hub",
    address: "450 Electric Blvd, Metro Central",
    city: "Metropolis",
    distanceKm: "1.2 km",
    totalChargers: 6,
    availableChargers: 4,
    chargers: [
      { id: 101, number: "CH-01", status: "AVAILABLE", powerKw: 150, connectorType: "CCS2" },
      { id: 102, number: "CH-02", status: "AVAILABLE", powerKw: 150, connectorType: "CCS2" },
      { id: 103, number: "CH-03", status: "OCCUPIED", powerKw: 50, connectorType: "Type 2" },
      { id: 104, number: "CH-04", status: "MAINTENANCE", powerKw: 50, connectorType: "Type 2" },
    ],
  },
  {
    id: 2,
    isMockData: true,
    name: "Westside Tech Plaza",
    address: "88 Silicon Way, Tech District",
    city: "Metropolis",
    distanceKm: "3.5 km",
    totalChargers: 8,
    availableChargers: 6,
    chargers: [
      { id: 201, number: "CH-01", status: "AVAILABLE", powerKw: 350, connectorType: "CCS2" },
      { id: 202, number: "CH-02", status: "AVAILABLE", powerKw: 150, connectorType: "CCS2" },
      { id: 203, number: "CH-03", status: "AVAILABLE", powerKw: 50, connectorType: "CHAdeMO" },
    ],
  },
  {
    id: 3,
    isMockData: true,
    name: "Airport Rapid Energy Depot",
    address: "Terminal 2 Ground Transport, Airport Ring Rd",
    city: "Metropolis",
    distanceKm: "7.8 km",
    totalChargers: 4,
    availableChargers: 1,
    chargers: [
      { id: 301, number: "CH-01", status: "OCCUPIED", powerKw: 150, connectorType: "CCS2" },
      { id: 302, number: "CH-02", status: "AVAILABLE", powerKw: 150, connectorType: "CCS2" },
      { id: 303, number: "CH-03", status: "OFFLINE", powerKw: 50, connectorType: "Type 2" },
    ],
  },
  {
    id: 4,
    isMockData: true,
    name: "GreenPark Eco Station",
    address: "12 Renewable Ave, Solar Meadows",
    city: "Metropolis",
    distanceKm: "11.0 km",
    totalChargers: 4,
    availableChargers: 4,
    chargers: [
      { id: 401, number: "CH-01", status: "AVAILABLE", powerKw: 50, connectorType: "Type 2" },
      { id: 402, number: "CH-02", status: "AVAILABLE", powerKw: 50, connectorType: "CCS2" },
    ],
  },
];

export const MOCK_VEHICLES = [
  {
    id: 1,
    isMockData: true,
    make: "Tesla",
    model: "Model 3 Long Range",
    licensePlate: "EV-902-TR",
    batteryCapacityKwh: 75.0,
    currentChargePercent: 42,
    connectorType: "CCS2",
  },
  {
    id: 2,
    isMockData: true,
    make: "Hyundai",
    model: "Ioniq 5 AWD",
    licensePlate: "EV-314-HY",
    batteryCapacityKwh: 72.6,
    currentChargePercent: 68,
    connectorType: "CCS2",
  },
];

export const MOCK_BOOKINGS = [
  {
    id: 1001,
    isMockData: true,
    stationName: "Downtown Supercharge Hub",
    chargerNumber: "CH-01 (150 kW)",
    vehiclePlate: "EV-902-TR (Tesla Model 3)",
    startTime: "2026-10-21T10:00:00Z",
    endTime: "2026-10-21T10:30:00Z",
    slotFormatted: "Tomorrow, 10:00 AM - 10:30 AM",
    status: "CONFIRMED",
    connectorType: "CCS2",
  },
  {
    id: 1002,
    isMockData: true,
    stationName: "Westside Tech Plaza",
    chargerNumber: "CH-02 (150 kW)",
    vehiclePlate: "EV-314-HY (Hyundai Ioniq 5)",
    startTime: "2026-10-18T14:30:00Z",
    endTime: "2026-10-18T15:00:00Z",
    slotFormatted: "Oct 18, 2026, 2:30 PM - 3:00 PM",
    status: "COMPLETED",
    connectorType: "CCS2",
  },
];
