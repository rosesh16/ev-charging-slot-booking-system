import { useState } from "react";
import { useAuth } from "../context/useAuth";

export default function AuthModal({ isOpen, onClose, initialMode = "login" }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [localError, setLocalError] = useState("");

  const { login, register, loading, error, clearError } = useAuth();

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    clearError();

    if (!email.trim() || !password) {
      setLocalError("Email and password are required.");
      return;
    }

    if (mode === "register") {
      if (!username.trim()) {
        setLocalError("Username is required.");
        return;
      }
      if (password.length < 8) {
        setLocalError("Password must be at least 8 characters long.");
        return;
      }

      const res = await register({
        email,
        username,
        password,
        phone_number: phoneNumber,
      });

      if (res.success) {
        onClose();
      }
    } else {
      const res = await login({ email, password });
      if (res.success) {
        onClose();
      }
    }
  };

  const displayedError = localError || error;

  return (
    <div className="auth-modal-backdrop" onClick={onClose} aria-hidden="true">
      <div
        id="auth-modal-dialog"
        className="auth-modal-dialog"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        <button
          type="button"
          className="auth-modal-close"
          onClick={onClose}
          aria-label="Close Authentication Dialog"
        >
          &times;
        </button>

        <div className="auth-modal-header">
          <div className="auth-modal-brand-icon">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
              <path d="M13 2L3 14h8l-1 8 11-13h-8l1-7z" />
            </svg>
          </div>
          <h2 id="auth-modal-title" className="auth-modal-title">
            {mode === "login" ? "Sign In to VoltSlot" : "Create a VoltSlot Account"}
          </h2>
          <p className="auth-modal-subtitle">
            {mode === "login"
              ? "Access your EV fleet, reserved charging slots, and quick bookings."
              : "Register to book 30-minute charging slots with guaranteed concurrency."}
          </p>
        </div>

        {displayedError && (
          <div className="auth-error-banner" role="alert">
            <span className="error-icon">&#9888;</span>
            <span>{displayedError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "register" && (
            <div className="form-group">
              <label htmlFor="reg-username">Username</label>
              <input
                id="reg-username"
                type="text"
                autoComplete="username"
                placeholder="e.g. ev_driver_01"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="auth-email">Email Address</label>
            <input
              id="auth-email"
              type="email"
              autoComplete="email"
              placeholder="driver@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
            />
            {mode === "register" && (
              <span className="field-hint">Must be at least 8 characters.</span>
            )}
          </div>

          {mode === "register" && (
            <div className="form-group">
              <label htmlFor="reg-phone">
                Phone Number <span className="optional-tag">(Optional)</span>
              </label>
              <input
                id="reg-phone"
                type="tel"
                autoComplete="tel"
                placeholder="+1 555 123 4567"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                disabled={loading}
              />
            </div>
          )}

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? (
              <span className="btn-spinner-row">
                <span className="spinner-dot" />
                <span>Connecting to DRF Backend...</span>
              </span>
            ) : mode === "login" ? (
              "Sign In"
            ) : (
              "Complete Registration"
            )}
          </button>
        </form>

        <div className="auth-modal-footer">
          {mode === "login" ? (
            <p>
              Don't have an account yet?{" "}
              <button
                type="button"
                className="switch-mode-btn"
                onClick={() => {
                  setMode("register");
                  clearError();
                  setLocalError("");
                }}
              >
                Create one now
              </button>
            </p>
          ) : (
            <p>
              Already registered?{" "}
              <button
                type="button"
                className="switch-mode-btn"
                onClick={() => {
                  setMode("login");
                  clearError();
                  setLocalError("");
                }}
              >
                Sign in here
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
