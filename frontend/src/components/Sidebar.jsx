import { useAuth } from "../context/useAuth";

export default function Sidebar({
  activeTab,
  onSelectTab,
  isMobileOpen,
  onCloseMobile,
  onOpenAuth,
}) {
  const { isAuthenticated, user, logout } = useAuth();

  const navItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      isProtected: false,
      icon: (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
        </svg>
      ),
    },
    {
      id: "stations",
      label: "Find Stations",
      isProtected: false,
      icon: (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
      ),
    },
    {
      id: "vehicles",
      label: "My Vehicles",
      isProtected: true,
      icon: (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9L2 12v4c0 .6.4 1 1 1h2" />
          <circle cx="7" cy="17" r="2" />
          <circle cx="17" cy="17" r="2" />
        </svg>
      ),
    },
    {
      id: "bookings",
      label: "My Bookings",
      isProtected: true,
      icon: (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
      ),
    },
  ];

  return (
    <>
      {isMobileOpen && (
        <div className="sidebar-backdrop" onClick={onCloseMobile} aria-hidden="true" />
      )}
      <aside className={`dashboard-sidebar ${isMobileOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-header">
          <div className="brand-group">
            <div className="brand-logo" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M13 2L3 14h8l-1 8 11-13h-8l1-7z" />
              </svg>
            </div>
            <div className="brand-text">
              <span className="brand-title">VoltSlot</span>
              <span className="brand-tagline">EV Charging Network</span>
            </div>
          </div>
          {isMobileOpen && (
            <button className="mobile-close-btn" onClick={onCloseMobile} aria-label="Close Navigation">
              &times;
            </button>
          )}
        </div>

        <nav className="sidebar-nav">
          <div className="nav-group-title">Navigation</div>
          <ul className="nav-list">
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={`nav-btn ${activeTab === item.id ? "active" : ""}`}
                  onClick={() => {
                    onSelectTab(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                  {item.id === "bookings" && isAuthenticated && (
                    <span className="nav-badge">1</span>
                  )}
                  {item.isProtected && !isAuthenticated && (
                    <span className="lock-icon" title="Sign in required for this view">
                      &#128274;
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          {isAuthenticated && user ? (
            <div className="sidebar-user-card">
              <div className="sidebar-user-header">
                <span className="sidebar-user-name">{user.username}</span>
                <span className="role-tag">{user.role || "DRIVER"}</span>
              </div>
              <span className="sidebar-user-email">{user.email}</span>
              <button
                type="button"
                className="sidebar-logout-btn"
                onClick={logout}
              >
                Sign Out
              </button>
            </div>
          ) : (
            <div className="sidebar-auth-prompt">
              <p className="auth-prompt-title">Sign in to VoltSlot</p>
              <p className="auth-prompt-desc">Access fleet management and booking reservations.</p>
              <button
                id="sidebar-signin-btn"
                type="button"
                className="sidebar-signin-btn"
                onClick={() => {
                  onOpenAuth("login");
                  if (onCloseMobile) onCloseMobile();
                }}
              >
                Sign In / Register
              </button>
            </div>
          )}

          <div className="system-health-pill">
            <span className="live-dot" />
            <span>DRF • 62 Tests Passing</span>
          </div>
        </div>
      </aside>
    </>
  );
}
