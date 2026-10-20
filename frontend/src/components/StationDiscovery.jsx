import { useState, useEffect } from "react";
import { fetchStationsWithChargers } from "../api/stations";

/**
 * Formats connector type for display without fabricating values.
 */
function formatConnectorType(connectorType) {
  if (!connectorType) return "Unknown";
  switch (connectorType) {
    case "TYPE_2":
      return "Type 2";
    case "CCS2":
      return "CCS2";
    case "CHADEMO":
      return "CHAdeMO";
    default:
      return connectorType;
  }
}

/**
 * Formats charger status text and CSS modifier class.
 */
function getStatusInfo(status) {
  switch (status) {
    case "AVAILABLE":
      return { label: "Available", className: "status-available" };
    case "OCCUPIED":
      return { label: "Occupied", className: "status-occupied" };
    case "MAINTENANCE":
      return { label: "Maintenance", className: "status-offline" };
    case "OFFLINE":
      return { label: "Offline", className: "status-offline" };
    default:
      return { label: status || "Unknown", className: "status-offline" };
  }
}

export default function StationDiscovery({
  searchQuery = "",
  onSelectStationForBooking,
  onStationsLoaded,
}) {
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedConnector, setSelectedConnector] = useState("ALL");

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await fetchStationsWithChargers();
        if (!ignore) {
          setStations(data);
          setLoading(false);
          if (onStationsLoaded) {
            onStationsLoaded(data);
          }
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load station data from DRF backend.");
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [onStationsLoaded]);

  const handleManualRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStationsWithChargers();
      setStations(data);
      if (onStationsLoaded) {
        onStationsLoaded(data);
      }
    } catch (err) {
      setError(err.message || "Failed to load station data from DRF backend.");
    } finally {
      setLoading(false);
    }
  };

  const filteredStations = stations.filter((st) => {
    const q = searchQuery.toLowerCase().trim();
    const nameMatch = st.name ? st.name.toLowerCase().includes(q) : false;
    const addressMatch = st.address ? st.address.toLowerCase().includes(q) : false;
    const cityMatch = st.city ? st.city.toLowerCase().includes(q) : false;
    const matchesSearch = !q || nameMatch || addressMatch || cityMatch;

    const matchesConnector =
      selectedConnector === "ALL" ||
      st.chargers.some(
        (c) =>
          c.connector_type === selectedConnector ||
          formatConnectorType(c.connector_type) === selectedConnector
      );

    return matchesSearch && matchesConnector;
  });

  return (
    <section className="station-discovery-section">
      <div className="section-header-row">
        <div>
          <h2 className="section-title">Charging Stations</h2>
          <p className="section-subtitle">
            Live infrastructure retrieved from Django REST Framework backend
          </p>
        </div>
        <div className="filter-pill-group">
          {["ALL", "CCS2", "Type 2", "CHAdeMO"].map((conn) => (
            <button
              key={conn}
              type="button"
              className={`filter-pill ${selectedConnector === conn ? "active" : ""}`}
              onClick={() => setSelectedConnector(conn)}
            >
              {conn === "ALL" ? "All Connectors" : conn}
            </button>
          ))}
        </div>
      </div>

      {/* Live Data Connection Banner */}
      <div className="live-data-banner">
        <span className="live-dot" />
        <span className="live-banner-text">
          <strong>Live Backend Data:</strong> Displaying verified records from{" "}
          <code>/api/stations/</code> and <code>/api/chargers/</code>.
        </span>
        <button
          type="button"
          className="refresh-btn"
          onClick={handleManualRefresh}
          disabled={loading}
          title="Refresh station list from API"
        >
          {loading ? "Refreshing..." : "↻ Refresh"}
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="station-loading-card">
          <div className="loading-spinner" />
          <p>Querying station network from Django REST API...</p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="station-error-card" role="alert">
          <div className="error-icon-box">&#9888;</div>
          <h3 className="error-title">Unable to Connect to Stations API</h3>
          <p className="error-desc">{error}</p>
          <button type="button" className="retry-btn" onClick={handleManualRefresh}>
            Retry Connection
          </button>
        </div>
      )}

      {/* Empty State (Database has 0 stations, or filters match 0) */}
      {!loading && !error && filteredStations.length === 0 && (
        <div className="empty-state-card">
          <div className="empty-state-icon">
            <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          </div>
          <h3 className="empty-state-title">
            {stations.length === 0
              ? "No Active Stations in Database"
              : "No Stations Match Your Filters"}
          </h3>
          <p className="empty-state-text">
            {stations.length === 0
              ? "The live database currently contains 0 active charging stations. New stations added via the Django admin or API will appear here in real time."
              : "Try adjusting your search terms or clearing the connector filter to view all stations."}
          </p>
          {selectedConnector !== "ALL" && (
            <button
              type="button"
              className="empty-state-reset-btn"
              onClick={() => setSelectedConnector("ALL")}
            >
              Clear Filters
            </button>
          )}
        </div>
      )}

      {/* Stations Grid */}
      {!loading && !error && filteredStations.length > 0 && (
        <div className="stations-grid">
          {filteredStations.map((station) => (
            <div key={station.id} className="station-card">
              <div className="station-card-header">
                <div>
                  <h3 className="station-name">{station.name}</h3>
                  <p className="station-address">
                    <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" fill="none" strokeWidth="2">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                    {station.address || "Address not specified"}
                  </p>
                </div>
                {station.city && <span className="city-pill">{station.city}</span>}
              </div>

              {/* Geographic Coordinates if present */}
              {(station.latitude || station.longitude) && (
                <div className="coordinates-tag">
                  <span>GPS: {station.latitude || "N/A"}, {station.longitude || "N/A"}</span>
                </div>
              )}

              <div className="station-card-chargers-summary">
                <div className="summary-pill">
                  <span className="dot-green" />
                  <span>
                    {station.availableChargers} / {station.totalChargers} Available
                  </span>
                </div>
                <span className="station-id-pill">Station #{station.id}</span>
              </div>

              {/* Installed Chargers List from Live API */}
              <div className="chargers-list">
                <div className="chargers-list-heading">
                  Installed Chargers ({station.chargers.length}):
                </div>
                {station.chargers.length === 0 ? (
                  <p className="no-chargers-note">No chargers currently linked to this station.</p>
                ) : (
                  <div className="chargers-chips">
                    {station.chargers.map((ch) => {
                      const { label, className } = getStatusInfo(ch.status);
                      const connectorLabel = formatConnectorType(ch.connector_type);
                      const powerDisplay = ch.power_kw ? `${parseFloat(ch.power_kw)} kW` : "N/A";

                      return (
                        <div key={ch.id} className={`charger-chip ${className}`}>
                          <div className="chip-left">
                            <span className="charger-num">{ch.name}</span>
                            <span className="charger-type">{connectorLabel}</span>
                          </div>
                          <div className="chip-right">
                            <span className="charger-power">{powerDisplay}</span>
                            <span className="charger-state-text">{label}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="station-card-footer">
                <button
                  type="button"
                  className="book-slot-btn"
                  disabled={station.chargers.length === 0}
                  onClick={() => onSelectStationForBooking && onSelectStationForBooking(station)}
                >
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                  <span>Select &amp; View Slots</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
