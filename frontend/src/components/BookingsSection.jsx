import { useState, useEffect, useMemo, useCallback } from "react";
import { useAuth } from "../context/useAuth";
import { fetchChargerAvailabilityApi } from "../api/stations";
import { fetchBookingsApi, createBookingApi, cancelBookingApi } from "../api/bookings";
import { fetchVehiclesApi } from "../api/vehicles";

/**
 * Computes 30-minute intervals between startIso and endIso,
 * flagging overlaps against bookedIntervals and past times.
 */
function computeSlotsFromAvailability(startIso, endIso, bookedIntervals = [], chargerStatus = "AVAILABLE", nowMs = Date.now()) {
  const startDate = new Date(startIso);
  const endDate = new Date(endIso);
  const slots = [];

  let current = new Date(startDate.getTime());
  const thirtyMinsMs = 30 * 60 * 1000;

  while (current.getTime() + thirtyMinsMs <= endDate.getTime()) {
    const slotStart = new Date(current.getTime());
    const slotEnd = new Date(current.getTime() + thirtyMinsMs);

    const formatUtc = (d) =>
      `${d.getUTCHours().toString().padStart(2, "0")}:${d.getUTCMinutes().toString().padStart(2, "0")}`;
    const timeLabel = `${formatUtc(slotStart)} - ${formatUtc(slotEnd)} UTC`;

    // Overlap condition: slotStart < bEnd && slotEnd > bStart
    const hasConflict = bookedIntervals.some((b) => {
      const bStart = new Date(b.start_time);
      const bEnd = new Date(b.end_time);
      return slotStart < bEnd && slotEnd > bStart;
    });

    const isPast = slotStart.getTime() <= nowMs;

    let status = "AVAILABLE";
    let isAvailable = true;

    if (isPast) {
      status = "PAST";
      isAvailable = false;
    } else if (hasConflict) {
      status = "BOOKED";
      isAvailable = false;
    } else if (chargerStatus !== "AVAILABLE") {
      status = chargerStatus;
      isAvailable = false;
    }

    slots.push({
      time: timeLabel,
      startIso: slotStart.toISOString(),
      endIso: slotEnd.toISOString(),
      status,
      isAvailable,
    });

    current = new Date(current.getTime() + thirtyMinsMs);
  }

  return slots;
}

export default function BookingsSection({
  selectedStationForBooking,
  stations = [],
  onSelectStation,
  onOpenAuth,
  onNavigate,
  onBookingsUpdated,
}) {
  const { isAuthenticated, token } = useAuth();

  // --- 1. User Bookings History State ---
  const [bookings, setBookings] = useState([]);
  const [bookingsFetchedAt, setBookingsFetchedAt] = useState(0);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingsError, setBookingsError] = useState(null);
  const [cancellingId, setCancellingId] = useState(null);
  const [bookingSuccessMsg, setBookingSuccessMsg] = useState(null);

  // --- 2. User Registered Vehicles State (for reservation dropdown) ---
  const [userVehicles, setUserVehicles] = useState([]);
  const [selectedVehicleId, setSelectedVehicleId] = useState("");

  // --- 3. Station & Charger Selection State ---
  const [activeStationId, setActiveStationId] = useState(null);
  const [activeChargerId, setActiveChargerId] = useState(null);

  // --- 4. Time Window / Date Offset (0 = Today, 1 = Tomorrow, 2 = In 2 Days) ---
  const [dayOffset, setDayOffset] = useState(1);

  // --- 5. Availability & Reservation Engine State ---
  const [availabilityData, setAvailabilityData] = useState(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityError, setAvailabilityError] = useState(null);
  const [userSelectedSlotIndex, setUserSelectedSlotIndex] = useState(0);
  const [reservationSubmitting, setReservationSubmitting] = useState(false);
  const [reservationError, setReservationError] = useState(null);

  // Resolve current station
  const currentStation = useMemo(() => {
    if (selectedStationForBooking) {
      return selectedStationForBooking;
    }
    if (activeStationId && stations.length > 0) {
      return stations.find((s) => s.id === activeStationId) || stations[0];
    }
    return stations.length > 0 ? stations[0] : null;
  }, [selectedStationForBooking, activeStationId, stations]);

  const chargers = useMemo(() => currentStation?.chargers || [], [currentStation]);

  // Target charger ID
  const targetChargerId = useMemo(() => {
    if (activeChargerId && chargers.some((c) => c.id === activeChargerId)) {
      return activeChargerId;
    }
    return chargers.length > 0 ? chargers[0].id : null;
  }, [activeChargerId, chargers]);

  const activeChargerObj = useMemo(
    () => chargers.find((c) => c.id === targetChargerId) || null,
    [chargers, targetChargerId]
  );
  const activeChargerStatus = activeChargerObj ? activeChargerObj.status : "AVAILABLE";

  // --- Fetch Bookings ---
  const loadBookings = useCallback(async () => {
    if (!token) {
      setBookings([]);
      return;
    }
    setBookingsLoading(true);
    setBookingsError(null);
    try {
      const data = await fetchBookingsApi(token);
      setBookings(data);
      setBookingsFetchedAt(Date.now());
      if (onBookingsUpdated) {
        onBookingsUpdated(data);
      }
    } catch (err) {
      setBookingsError(err.message || "Failed to load bookings.");
      setBookings([]);
    } finally {
      setBookingsLoading(false);
    }
  }, [token, onBookingsUpdated]);

  // --- Fetch User Vehicles for booking dropdown ---
  const loadUserVehicles = useCallback(async () => {
    if (!token) {
      setUserVehicles([]);
      return;
    }
    try {
      const vData = await fetchVehiclesApi(token);
      setUserVehicles(vData);
      if (vData.length > 0) {
        setSelectedVehicleId((prev) => (prev ? prev : vData[0].id));
      }
    } catch {
      setUserVehicles([]);
    }
  }, [token]);

  // Initial load effect for bookings and vehicles
  useEffect(() => {
    let ignore = false;
    if (!isAuthenticated || !token) {
      return;
    }

    async function loadInitial() {
      try {
        const [bData, vData] = await Promise.all([
          fetchBookingsApi(token),
          fetchVehiclesApi(token),
        ]);
        if (!ignore) {
          setBookings(bData);
          setBookingsFetchedAt(Date.now());
          setBookingsLoading(false);
          if (onBookingsUpdated) {
            onBookingsUpdated(bData);
          }
          setUserVehicles(vData);
          if (vData.length > 0) {
            setSelectedVehicleId((prev) => (prev ? prev : vData[0].id));
          }
        }
      } catch (err) {
        if (!ignore) {
          setBookingsError(err.message || "Failed to load bookings.");
          setBookingsLoading(false);
        }
      }
    }

    loadInitial();

    return () => {
      ignore = true;
    };
  }, [isAuthenticated, token, onBookingsUpdated]);

  // Calculate window start & end for availability based on dayOffset
  const getAvailabilityWindow = useCallback((offset) => {
    const base = new Date();
    base.setUTCDate(base.getUTCDate() + offset);

    if (offset === 0) {
      // Today: next whole hour to +6 hours
      const start = new Date(base.getTime());
      start.setUTCMinutes(0, 0, 0);
      if (start.getTime() <= Date.now()) {
        start.setUTCHours(start.getUTCHours() + 1);
      }
      const end = new Date(start.getTime() + 6 * 60 * 60 * 1000);
      return { startIso: start.toISOString(), endIso: end.toISOString() };
    }

    // Tomorrow or future: 09:00 UTC to 15:00 UTC (6 hours = 12 slots)
    base.setUTCHours(9, 0, 0, 0);
    const startIso = base.toISOString();
    const end = new Date(base.getTime() + 6 * 60 * 60 * 1000);
    const endIso = end.toISOString();
    return { startIso, endIso };
  }, []);

  // --- Query Availability ---
  const queryAvailability = useCallback(
    async (chargerId, offset = dayOffset) => {
      if (!chargerId) {
        setAvailabilityData(null);
        return null;
      }
      setAvailabilityLoading(true);
      setAvailabilityError(null);
      const { startIso, endIso } = getAvailabilityWindow(offset);

      try {
        const result = await fetchChargerAvailabilityApi(chargerId, startIso, endIso);
        result.queryTimestamp = Date.now();
        setAvailabilityData(result);
        return result;
      } catch (err) {
        setAvailabilityError(err.message || "Failed to query charger availability.");
        setAvailabilityData(null);
        return null;
      } finally {
        setAvailabilityLoading(false);
      }
    },
    [dayOffset, getAvailabilityWindow]
  );

  useEffect(() => {
    let ignore = false;
    if (!targetChargerId) {
      return;
    }

    const { startIso, endIso } = getAvailabilityWindow(dayOffset);
    fetchChargerAvailabilityApi(targetChargerId, startIso, endIso)
      .then((res) => {
        if (!ignore) {
          res.queryTimestamp = Date.now();
          setAvailabilityData(res);
          setAvailabilityLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setAvailabilityError(err.message || "Failed to query charger availability.");
          setAvailabilityLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [targetChargerId, dayOffset, getAvailabilityWindow]);

  // Compute live slots
  const computedSlots = useMemo(() => {
    if (!availabilityData) {
      return [];
    }
    return computeSlotsFromAvailability(
      availabilityData.start,
      availabilityData.end,
      availabilityData.booked_intervals,
      activeChargerStatus,
      availabilityData.queryTimestamp || 0
    );
  }, [availabilityData, activeChargerStatus]);


  // Derived effective slot index (defaults to user choice if available, or first available slot)
  const selectedSlotIndex = useMemo(() => {
    if (computedSlots.length === 0) return 0;
    if (computedSlots[userSelectedSlotIndex]?.isAvailable) {
      return userSelectedSlotIndex;
    }
    const firstAvail = computedSlots.findIndex((s) => s.isAvailable);
    return firstAvail !== -1 ? firstAvail : 0;
  }, [computedSlots, userSelectedSlotIndex]);

  const [confirmingCancelId, setConfirmingCancelId] = useState(null);

  // --- Handle Booking Cancellation ---
  const handleCancelBooking = async (bookingId) => {
    if (!token) return;

    setCancellingId(bookingId);
    setConfirmingCancelId(null);
    setBookingSuccessMsg(null);
    setBookingsError(null);

    try {
      await cancelBookingApi(bookingId, token);
      setBookingSuccessMsg(`Booking #${bookingId} successfully cancelled.`);
      await loadBookings();
      if (targetChargerId) {
        await queryAvailability(targetChargerId, dayOffset);
      }
    } catch (err) {
      setBookingsError(err.message || "Failed to cancel booking.");
    } finally {
      setCancellingId(null);
    }
  };

  // --- Handle Reserve Slot ---
  const handleReserveSlot = async () => {
    if (!isAuthenticated) {
      onOpenAuth("login");
      return;
    }

    setReservationError(null);
    setBookingSuccessMsg(null);

    if (!targetChargerId) {
      setReservationError("Please select a charging station and charger.");
      return;
    }

    if (!selectedVehicleId) {
      setReservationError("Please select a registered vehicle for this booking.");
      return;
    }

    const targetSlot = computedSlots[selectedSlotIndex];
    if (!targetSlot || !targetSlot.isAvailable) {
      setReservationError("Please select an available 30-minute time slot.");
      return;
    }

    setReservationSubmitting(true);

    try {
      // 1. Pre-submission freshness check: query availability right before submission
      const freshAvailability = await queryAvailability(targetChargerId, dayOffset);
      if (freshAvailability) {
        const freshSlots = computeSlotsFromAvailability(
          freshAvailability.start,
          freshAvailability.end,
          freshAvailability.booked_intervals,
          activeChargerStatus,
          Date.now()
        );
        const matchingSlot = freshSlots.find((s) => s.startIso === targetSlot.startIso);
        if (!matchingSlot || !matchingSlot.isAvailable) {
          setReservationError(
            "This slot was just booked by another user. Please choose another time slot."
          );
          setReservationSubmitting(false);
          return;
        }
      }

      // 2. Submit booking to DRF API
      const payload = {
        charger: Number(targetChargerId),
        vehicle: Number(selectedVehicleId),
        start_time: targetSlot.startIso,
        end_time: targetSlot.endIso,
      };

      const newBooking = await createBookingApi(payload, token);
      setBookingSuccessMsg(
        `Booking Confirmed! Reservation #${newBooking.id} reserved for ${targetSlot.time}.`
      );

      // 3. Refresh user bookings and charger availability
      await loadBookings();
      await queryAvailability(targetChargerId, dayOffset);
    } catch (err) {
      if (err.status === 409) {
        setReservationError(
          "Conflict: This charger is already booked for the requested time slot. Availability updated."
        );
        // Refresh availability immediately on 409
        queryAvailability(targetChargerId, dayOffset);
      } else {
        setReservationError(err.message || "Failed to reserve slot. Please review requirements.");
      }
    } finally {
      setReservationSubmitting(false);
    }
  };

  return (
    <section className="bookings-section-container">
      {/* Section Header */}
      <div className="section-header-row">
        <div>
          <h2 className="section-title">My Bookings &amp; Reservation Engine</h2>
          <p className="section-subtitle">
            Manage reserved slots and book live 30-minute availability intervals
          </p>
        </div>
        {isAuthenticated && (
          <button
            type="button"
            className="refresh-btn"
            onClick={() => {
              loadBookings();
              loadUserVehicles();
              if (targetChargerId) queryAvailability(targetChargerId, dayOffset);
            }}
            disabled={bookingsLoading || availabilityLoading}
          >
            {bookingsLoading ? "Refreshing..." : "↻ Refresh Live Data"}
          </button>
        )}
      </div>

      <div className="live-data-banner">
        <div className="live-banner-text">
          <span>
            <strong>Live DRF Connected:</strong> Reservations are created and cancelled via{" "}
            <code>/api/bookings/</code>. Real-time availability enforced via PostgreSQL 17 exclusion constraints.
          </span>
        </div>
        <span className="phase-tag live-badge">Live API Connected</span>
      </div>

      {bookingSuccessMsg && (
        <div className="auth-alert success" role="alert" style={{ marginBottom: "16px" }}>
          <span>&#10004; {bookingSuccessMsg}</span>
        </div>
      )}

      {/* Grid: Upcoming Bookings on Left, 30-Min Reservation Engine on Right */}
      <div className="bookings-layout-grid">
        {/* Left Column: Live Bookings History */}
        <div className="bookings-list-column">
          <h3 className="column-title">
            <span>My Bookings History</span>
            <span className="count-pill">
              {isAuthenticated ? bookings.length : 0}
            </span>
          </h3>

          {!isAuthenticated ? (
            <div className="empty-state-card mini">
              <div className="empty-state-icon">
                <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <h4 className="empty-state-title">Sign In Required</h4>
              <p className="empty-state-text">
                Please sign in to view your personal booking history and manage reservations.
              </p>
              <button
                type="button"
                className="empty-state-reset-btn"
                onClick={() => onOpenAuth("login")}
              >
                Sign In to View Bookings
              </button>
            </div>
          ) : bookingsLoading && bookings.length === 0 ? (
            <div className="slot-loading-box">
              <span className="spinner-dot" />
              <span>Loading your live bookings...</span>
            </div>
          ) : bookingsError && bookings.length === 0 ? (
            <div className="slot-error-box" role="alert">
              <span>&#9888; {bookingsError}</span>
              <button type="button" className="retry-sm-btn" onClick={loadBookings}>
                Retry
              </button>
            </div>
          ) : bookings.length === 0 ? (
            <div className="empty-state-card mini">
              <div className="empty-state-icon">
                <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                </svg>
              </div>
              <h4 className="empty-state-title">No Active Bookings</h4>
              <p className="empty-state-text">
                You have no active or previous charging reservations. Select a station on the right to reserve a 30-minute slot.
              </p>
            </div>
          ) : (
            <div className="bookings-cards-stack">
              {bookings.map((booking) => {
                const isConfirmed = booking.status === "CONFIRMED";
                const isCancelled = booking.status === "CANCELLED";
                const startDate = new Date(booking.start_time);
                const endDate = new Date(booking.end_time);
                const isFuture = startDate.getTime() > bookingsFetchedAt;

                const formattedTime = `${startDate.toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })}, ${startDate.getUTCHours().toString().padStart(2, "0")}:${startDate
                  .getUTCMinutes()
                  .toString()
                  .padStart(2, "0")} - ${endDate
                  .getUTCHours()
                  .toString()
                  .padStart(2, "0")}:${endDate.getUTCMinutes().toString().padStart(2, "0")} UTC`;

                const stationName = booking.charger?.station?.name || "EV Charging Station";
                const chargerLabel = booking.charger
                  ? `${booking.charger.name} (${parseFloat(booking.charger.power_kw)} kW ${booking.charger.connector_type})`
                  : `Charger #${booking.charger}`;

                const vehicleLabel = booking.vehicle
                  ? `${booking.vehicle.make} ${booking.vehicle.model} (${booking.vehicle.registration_number})`
                  : "Vehicle N/A";

                let statusBadgeClass = "status-completed";
                if (isConfirmed) statusBadgeClass = "status-confirmed";
                if (isCancelled) statusBadgeClass = "status-cancelled";

                return (
                  <div key={booking.id} className="booking-card">
                    <div className="booking-card-top">
                      <div>
                        <h4 className="booking-station-name">{stationName}</h4>
                        <span className="booking-charger-num">{chargerLabel}</span>
                      </div>
                      <span className={`status-pill ${statusBadgeClass}`}>
                        {booking.status}
                      </span>
                    </div>

                    <div className="booking-card-details">
                      <div className="detail-item">
                        <span className="detail-label">Vehicle</span>
                        <span className="detail-value">{vehicleLabel}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Reserved Window</span>
                        <span className="detail-value highlighted">{formattedTime}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Booking ID</span>
                        <span className="detail-value">#{booking.id} (30 min)</span>
                      </div>
                    </div>

                    <div className="booking-card-actions">
                      {isConfirmed && isFuture ? (
                        confirmingCancelId === booking.id ? (
                          <div className="cancel-confirm-row">
                            <span className="confirm-text">Cancel reservation?</span>
                            <button
                              type="button"
                              className="action-btn-danger"
                              onClick={() => handleCancelBooking(booking.id)}
                              disabled={cancellingId === booking.id}
                            >
                              {cancellingId === booking.id ? "Cancelling..." : "Yes, Cancel"}
                            </button>
                            <button
                              type="button"
                              className="action-btn-outline"
                              onClick={() => setConfirmingCancelId(null)}
                              disabled={cancellingId === booking.id}
                            >
                              Keep
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="action-btn-danger"
                            onClick={() => setConfirmingCancelId(booking.id)}
                            disabled={cancellingId === booking.id}
                          >
                            Cancel Slot
                          </button>
                        )
                      ) : isCancelled ? (
                        <span className="completed-note">
                          Cancelled {booking.cancelled_at ? new Date(booking.cancelled_at).toLocaleTimeString() : ""}
                        </span>
                      ) : (
                        <span className="completed-note">Session concluded (read-only)</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: 30-Minute Live Reservation Engine */}
        <div className="calendar-placeholder-column">
          <div className="calendar-header-box">
            <div>
              <h3 className="column-title">
                30-Minute Slot Reservation
                <span className="phase-tag live-badge">Live API Engine</span>
              </h3>
              <p className="column-subtitle">
                {currentStation
                  ? `Station: ${currentStation.name} (${currentStation.city || "Urban Zone"})`
                  : "No station selected. Select a station below to query live availability."}
              </p>
            </div>
          </div>

          {/* Station selector if available */}
          {stations.length > 1 && (
            <div className="charger-select-strip">
              <span className="select-strip-label">Select Station:</span>
              <select
                className="station-select-dropdown"
                value={currentStation?.id || ""}
                onChange={(e) => {
                  const st = stations.find((s) => s.id === Number(e.target.value));
                  if (st) {
                    if (onSelectStation) onSelectStation(st);
                    setActiveStationId(st.id);
                    if (st.chargers && st.chargers.length > 0) {
                      setActiveChargerId(st.chargers[0].id);
                    }
                  }
                }}
              >
                {stations.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.name} — {st.city} ({st.chargers?.length || 0} chargers)
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Charger selector strip */}
          {chargers.length > 0 && (
            <div className="charger-select-strip">
              <span className="select-strip-label">Select Charger:</span>
              <div className="charger-pills-row">
                {chargers.map((ch) => (
                  <button
                    key={ch.id}
                    type="button"
                    className={`charger-select-pill ${targetChargerId === ch.id ? "active" : ""}`}
                    onClick={() => {
                      setActiveChargerId(ch.id);
                      queryAvailability(ch.id, dayOffset);
                    }}
                  >
                    <span>{ch.name}</span>
                    <span className="pill-power">{parseFloat(ch.power_kw)} kW</span>
                    <span className={`pill-status-dot dot-${ch.status.toLowerCase()}`} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Charger status warning if OFFLINE or MAINTENANCE */}
          {activeChargerObj && activeChargerObj.status !== "AVAILABLE" && (
            <div className="charger-offline-banner">
              <span>&#9888; Charger {activeChargerObj.name} is currently <strong>{activeChargerObj.status}</strong>. Bookings cannot be accepted on inactive or offline chargers.</span>
            </div>
          )}

          {/* Day selection tabs */}
          <div className="day-select-strip">
            <span className="select-strip-label">Booking Date:</span>
            <div className="day-pills-row">
              <button
                type="button"
                className={`day-select-pill ${dayOffset === 0 ? "active" : ""}`}
                onClick={() => setDayOffset(0)}
              >
                Today
              </button>
              <button
                type="button"
                className={`day-select-pill ${dayOffset === 1 ? "active" : ""}`}
                onClick={() => setDayOffset(1)}
              >
                Tomorrow
              </button>
              <button
                type="button"
                className={`day-select-pill ${dayOffset === 2 ? "active" : ""}`}
                onClick={() => setDayOffset(2)}
              >
                In 2 Days
              </button>
            </div>
          </div>

          {/* Vehicle Selector for Authenticated Driver */}
          {isAuthenticated && (
            <div className="vehicle-selector-panel">
              <label htmlFor="slot-vehicle-select" className="select-strip-label">
                Vehicle for Reservation:
              </label>
              {userVehicles.length === 0 ? (
                <div className="no-vehicles-warning">
                  <span>&#9888; You have no registered vehicles.</span>
                  {onNavigate && (
                    <button
                      type="button"
                      className="inline-link-btn"
                      onClick={() => onNavigate("vehicles")}
                    >
                      + Register an EV to Book
                    </button>
                  )}
                </div>
              ) : (
                <select
                  id="slot-vehicle-select"
                  className="vehicle-select-dropdown"
                  value={selectedVehicleId}
                  onChange={(e) => setSelectedVehicleId(Number(e.target.value))}
                >
                  {userVehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.make} {v.model} — {v.registration_number}{" "}
                      {v.battery_capacity_kwh ? `(${v.battery_capacity_kwh} kWh)` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* API Contract Callout */}
          <div className="api-contract-callout">
            <div className="callout-header">
              <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span>
                {availabilityData
                  ? `Live Availability Response (Charger #${targetChargerId})`
                  : "Charger Availability Query"}
              </span>
            </div>
            <code>
              {availabilityData
                ? `GET /api/chargers/${targetChargerId}/availability/?start=${availabilityData.start}&end=${availabilityData.end}`
                : "GET /api/chargers/<id>/availability/?start=<ISO>&end=<ISO>"}
            </code>
            <p className="callout-desc">
              {availabilityData
                ? `Returned ${availabilityData.booked_intervals.length} conflicting booking interval(s). 30-min slots computed mathematically.`
                : "Querying live availability intervals."}
            </p>
          </div>

          {availabilityLoading && (
            <div className="slot-loading-box">
              <span className="spinner-dot" />
              <span>Querying live charger availability...</span>
            </div>
          )}

          {availabilityError && (
            <div className="slot-error-box" role="alert">
              <span>&#9888; {availabilityError}</span>
              <button
                type="button"
                className="retry-sm-btn"
                onClick={() => queryAvailability(targetChargerId, dayOffset)}
              >
                Retry
              </button>
            </div>
          )}

          {reservationError && (
            <div className="slot-error-box" role="alert">
              <span>&#9888; {reservationError}</span>
            </div>
          )}

          {/* 30-Minute Slots Grid */}
          {!availabilityLoading && computedSlots.length > 0 && (
            <div className="slots-grid-mockup">
              <div className="slots-grid-label">
                <span>Select 30-Minute Slot Window:</span>
                <span className="slots-subtext">(Exactly 30 minutes duration enforced)</span>
              </div>
              <div className="slots-tiles">
                {computedSlots.map((slot, idx) => (
                  <button
                    key={slot.startIso}
                    type="button"
                    className={`slot-tile ${slot.isAvailable ? "available" : "unavailable"} ${
                      selectedSlotIndex === idx ? "selected" : ""
                    }`}
                    disabled={!slot.isAvailable || reservationSubmitting}
                    onClick={() => setUserSelectedSlotIndex(idx)}
                  >
                    <span className="slot-time">{slot.time}</span>
                    <span className="slot-badge">
                      {slot.isAvailable ? "Available" : slot.status}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Reservation Action Footer */}
          <div className="slot-booking-action-footer">
            <div className="selected-slot-summary">
              <span className="summary-label">Selected Reservation:</span>
              <span className="summary-val">
                {computedSlots[selectedSlotIndex]?.time || "None selected"} (30 mins)
              </span>
            </div>

            {isAuthenticated ? (
              <button
                type="button"
                className="confirm-slot-btn"
                disabled={
                  reservationSubmitting ||
                  !computedSlots[selectedSlotIndex]?.isAvailable ||
                  !selectedVehicleId ||
                  activeChargerStatus !== "AVAILABLE"
                }
                onClick={handleReserveSlot}
              >
                {reservationSubmitting
                  ? "Verifying & Reserving..."
                  : "Reserve 30-Min Slot"}
              </button>
            ) : (
              <button
                type="button"
                className="confirm-slot-btn"
                style={{ cursor: "pointer", opacity: 1 }}
                onClick={() => onOpenAuth("login")}
              >
                Sign In to Reserve
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
