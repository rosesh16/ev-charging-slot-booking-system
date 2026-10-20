import { useAuth } from "../context/useAuth";

export default function TopNav({
  activeTab,
  onOpenMobile,
  searchQuery,
  onSearchChange,
  onOpenAuth,
}) {
  const { isAuthenticated, user, logout } = useAuth();

  const getTabTitle = () => {
    switch (activeTab) {
      case "stations":
        return { title: "Find Charging Stations", subtitle: "Explore nearby charging infrastructure" };
      case "vehicles":
        return { title: "My Registered EVs", subtitle: "Manage vehicles and battery compatibility" };
      case "bookings":
        return { title: "My Reservations", subtitle: "View and manage charging slot bookings" };
      default:
        return { title: "Charging Dashboard", subtitle: "Real-time overview of stations and upcoming slots" };
    }
  };

  const { title, subtitle } = getTabTitle();

  const getUserInitials = () => {
    if (!user) return "DR";
    if (user.username) return user.username.slice(0, 2).toUpperCase();
    if (user.email) return user.email.slice(0, 2).toUpperCase();
    return "DR";
  };

  return (
    <header className="top-nav">
      <div className="top-nav-left">
        <button
          type="button"
          className="mobile-hamburger-btn"
          onClick={onOpenMobile}
          aria-label="Open Navigation Menu"
        >
          <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" strokeWidth="2" fill="none">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        <div className="header-titles">
          <h1 className="header-page-title">{title}</h1>
          <p className="header-page-subtitle">{subtitle}</p>
        </div>
      </div>

      <div className="top-nav-right">
        <div className="search-bar">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search stations, cities..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            aria-label="Search"
          />
        </div>

        <div className="mock-data-pill live-connected" title="Live Django REST Framework APIs active">
          <span className="mock-bullet live-dot" />
          <span>Live APIs Active</span>
        </div>

        {isAuthenticated && user ? (
          <div className="user-profile-box">
            <div className="user-avatar" title={user.email} aria-label="User avatar">
              <span>{getUserInitials()}</span>
            </div>
            <div className="user-info-text">
              <span className="user-name">{user.username}</span>
              <span className="user-role">{user.role || "DRIVER"}</span>
            </div>
            <button
              type="button"
              className="logout-nav-btn"
              onClick={logout}
              title="Sign out of your session on this device"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <div className="auth-nav-actions">
            <button
              id="top-nav-sign-in-btn"
              type="button"
              className="btn-signin-nav"
              onClick={() => onOpenAuth("login")}
            >
              Sign In
            </button>
            <button
              id="top-nav-register-btn"
              type="button"
              className="btn-register-nav"
              onClick={() => onOpenAuth("register")}
            >
              Register
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
