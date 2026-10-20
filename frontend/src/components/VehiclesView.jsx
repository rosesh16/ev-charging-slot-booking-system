import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/useAuth";
import { fetchVehiclesApi, createVehicleApi } from "../api/vehicles";

export default function VehiclesView({ onOpenAuth, onVehiclesUpdated }) {
  const { isAuthenticated, token } = useAuth();

  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Add Vehicle Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [regNumber, setRegNumber] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [batteryCapacity, setBatteryCapacity] = useState("");
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [formSuccess, setFormSuccess] = useState(null);

  const loadVehicles = useCallback(async () => {
    if (!token) {
      setVehicles([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVehiclesApi(token);
      setVehicles(data);
      if (onVehiclesUpdated) {
        onVehiclesUpdated(data);
      }
    } catch (err) {
      setError(err.message || "Failed to load vehicles.");
      setVehicles([]);
    } finally {
      setLoading(false);
    }
  }, [token, onVehiclesUpdated]);

  useEffect(() => {
    let ignore = false;
    if (!isAuthenticated || !token) {
      return;
    }

    async function load() {
      try {
        const data = await fetchVehiclesApi(token);
        if (!ignore) {
          setVehicles(data);
          setLoading(false);
          if (onVehiclesUpdated) {
            onVehiclesUpdated(data);
          }
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load vehicles.");
          setVehicles([]);
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      ignore = true;
    };
  }, [isAuthenticated, token, onVehiclesUpdated]);

  const handleOpenAddForm = () => {
    setFormError(null);
    setFormSuccess(null);
    setRegNumber("");
    setMake("");
    setModel("");
    setBatteryCapacity("");
    setShowAddForm(true);
  };

  const handleCloseAddForm = () => {
    setShowAddForm(false);
    setFormError(null);
    setFormSuccess(null);
  };

  const handleCreateVehicle = async (e) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);

    const cleanReg = regNumber.trim().toUpperCase();
    const cleanMake = make.trim();
    const cleanModel = model.trim();

    if (!cleanReg) {
      setFormError("Registration number is required.");
      return;
    }
    if (!cleanMake) {
      setFormError("Make (manufacturer) is required.");
      return;
    }
    if (!cleanModel) {
      setFormError("Model is required.");
      return;
    }

    let parsedBattery = null;
    if (batteryCapacity.trim() !== "") {
      const val = parseFloat(batteryCapacity.trim());
      if (Number.isNaN(val) || val <= 0 || val > 999.99) {
        setFormError("Battery capacity must be a positive number up to 999.99 kWh.");
        return;
      }
      parsedBattery = val.toFixed(2);
    }

    setFormSubmitting(true);
    try {
      const payload = {
        registration_number: cleanReg,
        make: cleanMake,
        model: cleanModel,
      };
      if (parsedBattery !== null) {
        payload.battery_capacity_kwh = parsedBattery;
      }

      await createVehicleApi(payload, token);
      setFormSuccess(`Vehicle "${cleanReg}" successfully registered!`);

      // Refresh vehicle list
      await loadVehicles();

      // Reset form after a short delay
      setTimeout(() => {
        handleCloseAddForm();
      }, 1200);
    } catch (err) {
      setFormError(err.message || "Failed to register vehicle. Please review your input.");
    } finally {
      setFormSubmitting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <section className="vehicles-view-container">
        <div className="section-header-row">
          <div>
            <h2 className="section-title">My Registered Vehicles</h2>
            <p className="section-subtitle">
              Manage EV fleet, battery capacities, and compatible connector ports
            </p>
          </div>
        </div>

        <div className="auth-required-card">
          <div className="auth-lock-icon">
            <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h3 className="auth-required-title">Authentication Required</h3>
          <p className="auth-required-text">
            Sign in with your driver account to register and manage your electric vehicles.
          </p>
          <div className="auth-required-actions">
            <button
              type="button"
              className="btn-primary-action"
              onClick={() => onOpenAuth("login")}
            >
              Sign In to View Fleet
            </button>
            <button
              type="button"
              className="btn-secondary-action"
              onClick={() => onOpenAuth("register")}
            >
              Create Account
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="vehicles-view-container">
      <div className="section-header-row">
        <div>
          <h2 className="section-title">My Registered Vehicles</h2>
          <p className="section-subtitle">
            Manage EV fleet, battery capacities, and compatible connector ports
          </p>
        </div>
        <div className="header-actions-group">
          <button
            type="button"
            className="refresh-btn"
            onClick={loadVehicles}
            disabled={loading}
            title="Refresh vehicles from DRF backend"
          >
            {loading ? "Refreshing..." : "↻ Refresh"}
          </button>
          <button
            type="button"
            className="btn-register-nav"
            onClick={handleOpenAddForm}
          >
            + Register New EV
          </button>
        </div>
      </div>

      <div className="live-data-banner">
        <div className="live-banner-text">
          <span>
            <strong>Live DRF Connected:</strong> Displaying private vehicles owned by your account via <code>/api/vehicles/</code>.
          </span>
        </div>
        <span className="phase-tag live-badge">Live API Connected</span>
      </div>

      {/* Add Vehicle Modal / Form */}
      {showAddForm && (
        <div className="modal-overlay" onClick={handleCloseAddForm} role="presentation">
          <div
            className="modal-card"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-vehicle-title"
          >
            <div className="modal-header">
              <div className="modal-title-group">
                <h3 id="add-vehicle-title" className="modal-title">Register Electric Vehicle</h3>
                <p className="modal-subtitle">Add your EV to reserve charging slots</p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={handleCloseAddForm}
                aria-label="Close"
              >
                &times;
              </button>
            </div>

            {formError && (
              <div className="auth-alert error" role="alert">
                <span>&#9888; {formError}</span>
              </div>
            )}

            {formSuccess && (
              <div className="auth-alert success" role="alert">
                <span>&#10004; {formSuccess}</span>
              </div>
            )}

            <form onSubmit={handleCreateVehicle} className="auth-form">
              <div className="form-group">
                <label htmlFor="veh-reg-number">Registration / License Plate *</label>
                <input
                  id="veh-reg-number"
                  type="text"
                  required
                  maxLength={20}
                  placeholder="e.g. MH02CB1234 or EV-902-TR"
                  value={regNumber}
                  onChange={(e) => setRegNumber(e.target.value.toUpperCase())}
                  disabled={formSubmitting}
                />
                <span className="field-hint">Unique vehicle plate identifier (max 20 chars).</span>
              </div>

              <div className="form-group">
                <label htmlFor="veh-make">Make (Manufacturer) *</label>
                <input
                  id="veh-make"
                  type="text"
                  required
                  maxLength={100}
                  placeholder="e.g. Tesla, Hyundai, Tata"
                  value={make}
                  onChange={(e) => setMake(e.target.value)}
                  disabled={formSubmitting}
                />
              </div>

              <div className="form-group">
                <label htmlFor="veh-model">Model *</label>
                <input
                  id="veh-model"
                  type="text"
                  required
                  maxLength={100}
                  placeholder="e.g. Model 3, Ioniq 5, Nexon EV"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  disabled={formSubmitting}
                />
              </div>

              <div className="form-group">
                <label htmlFor="veh-battery">Battery Capacity (kWh) <span className="optional-tag">(Optional)</span></label>
                <input
                  id="veh-battery"
                  type="number"
                  step="0.01"
                  min="0.1"
                  max="999.99"
                  placeholder="e.g. 75.00"
                  value={batteryCapacity}
                  onChange={(e) => setBatteryCapacity(e.target.value)}
                  disabled={formSubmitting}
                />
                <span className="field-hint">Total battery pack rating in kWh (e.g. 50.0 to 120.0).</span>
              </div>

              <div className="modal-actions-row">
                <button
                  type="button"
                  className="btn-secondary-action"
                  onClick={handleCloseAddForm}
                  disabled={formSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="auth-submit-btn"
                  disabled={formSubmitting}
                >
                  {formSubmitting ? "Registering..." : "Register Vehicle"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="station-loading-card">
          <div className="loading-spinner" />
          <span>Loading your registered vehicles...</span>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="station-error-card" role="alert">
          <div className="error-icon-box">&#9888;</div>
          <h3 className="error-title">Failed to Load Vehicles</h3>
          <p className="error-desc">{error}</p>
          <button type="button" className="retry-btn" onClick={loadVehicles}>
            Retry Loading
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && vehicles.length === 0 && (
        <div className="empty-state-card">
          <div className="empty-state-icon">
            <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9L2 12v4c0 .6.4 1 1 1h2" />
              <circle cx="7" cy="17" r="2" />
              <circle cx="17" cy="17" r="2" />
            </svg>
          </div>
          <h3 className="empty-state-title">No Vehicles Registered</h3>
          <p className="empty-state-text">
            You haven't registered any electric vehicles yet. Add your vehicle to begin reserving charging slots.
          </p>
          <button
            type="button"
            className="empty-state-reset-btn"
            onClick={handleOpenAddForm}
          >
            + Register Your First EV
          </button>
        </div>
      )}

      {/* Vehicles Grid */}
      {!loading && !error && vehicles.length > 0 && (
        <div className="vehicles-grid">
          {vehicles.map((vehicle) => {
            const registeredDate = vehicle.created_at
              ? new Date(vehicle.created_at).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })
              : null;

            return (
              <div key={vehicle.id} className="vehicle-card">
                <div className="vehicle-card-top">
                  <div className="vehicle-icon-box">
                    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9L2 12v4c0 .6.4 1 1 1h2" />
                      <circle cx="7" cy="17" r="2" />
                      <circle cx="17" cy="17" r="2" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="vehicle-model">{vehicle.make} {vehicle.model}</h3>
                    <span className="vehicle-plate">{vehicle.registration_number}</span>
                  </div>
                  <span className="status-pill status-confirmed">Active Fleet</span>
                </div>

                <div className="vehicle-stats-row">
                  <div className="stat-box">
                    <span className="stat-label">Battery Capacity</span>
                    <span className="stat-value highlighted">
                      {vehicle.battery_capacity_kwh ? `${vehicle.battery_capacity_kwh} kWh` : "Not specified"}
                    </span>
                  </div>
                  <div className="stat-box">
                    <span className="stat-label">Vehicle ID</span>
                    <span className="stat-value">#{vehicle.id}</span>
                  </div>
                  <div className="stat-box">
                    <span className="stat-label">Registered On</span>
                    <span className="stat-value">{registeredDate || "N/A"}</span>
                  </div>
                </div>

                <div className="vehicle-card-footer">
                  <span className="vehicle-plate-info">
                    Owner ID: <code>{vehicle.owner}</code>
                  </span>
                  <span className="completed-note">Managed via DRF</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
