export default function SummaryCards({
  onNavigate,
  liveStationsCount,
  liveChargersCount,
  liveVehiclesCount,
  liveBookingsCount,
  isAuthenticated,
}) {
  const isLiveStationsReady = liveStationsCount !== null && liveStationsCount !== undefined;
  const isLiveVehiclesReady = isAuthenticated && liveVehiclesCount !== null && liveVehiclesCount !== undefined;
  const isLiveBookingsReady = isAuthenticated && liveBookingsCount !== null && liveBookingsCount !== undefined;

  const cards = [
    {
      id: "stations",
      title: "Live Stations",
      value: isLiveStationsReady ? liveStationsCount : 0,
      subtext: isLiveStationsReady
        ? `${liveChargersCount ?? 0} chargers deployed in network`
        : "Loading live stations...",
      badge: isLiveStationsReady ? "Live DRF Data" : "Connecting...",
      badgeType: "success",
      icon: (
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
      ),
      actionLabel: "Find Stations &rarr;",
      tabTarget: "stations",
    },
    {
      id: "vehicles",
      title: "Registered Vehicles",
      value: isAuthenticated
        ? (isLiveVehiclesReady ? liveVehiclesCount : "...")
        : "—",
      subtext: isAuthenticated
        ? (isLiveVehiclesReady ? `${liveVehiclesCount} vehicle(s) in fleet` : "Loading vehicles...")
        : "Sign in to view your EV fleet",
      badge: isAuthenticated
        ? (isLiveVehiclesReady ? "Live DRF Data" : "Loading...")
        : "Driver Login",
      badgeType: isAuthenticated ? "success" : "info",
      icon: (
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9L2 12v4c0 .6.4 1 1 1h2" />
          <circle cx="7" cy="17" r="2" />
          <circle cx="17" cy="17" r="2" />
        </svg>
      ),
      actionLabel: "Manage Vehicles &rarr;",
      tabTarget: "vehicles",
    },
    {
      id: "bookings",
      title: "Active Bookings",
      value: isAuthenticated
        ? (isLiveBookingsReady ? liveBookingsCount : "...")
        : "—",
      subtext: isAuthenticated
        ? (isLiveBookingsReady ? `${liveBookingsCount} confirmed reservation(s)` : "Loading bookings...")
        : "Sign in to view reservations",
      badge: isAuthenticated
        ? (isLiveBookingsReady ? "Live DRF Data" : "Loading...")
        : "Driver Login",
      badgeType: isAuthenticated ? "success" : "warning",
      icon: (
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
      ),
      actionLabel: "View Slots &rarr;",
      tabTarget: "bookings",
    },
    {
      id: "guard",
      title: "Concurrency Guard",
      value: "Zero-Collision",
      subtext: "PostgreSQL 17 btree_gist constraint",
      badge: "System Enforced",
      badgeType: "accent",
      icon: (
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      ),
      actionLabel: "Availability Engine &rarr;",
      tabTarget: "bookings",
    },
  ];

  return (
    <section className="summary-cards-container" aria-label="Dashboard Overview Summary">
      <div className="section-header-row">
        <h2 className="section-title">Network Overview</h2>
        <div className="metrics-legend">
          <span className="legend-live">&bull; Live DRF APIs Connected</span>
          {!isAuthenticated && (
            <span className="legend-mock">&bull; Sign in to load private driver fleet &amp; bookings</span>
          )}
        </div>
      </div>

      <div className="summary-cards-grid">
        {cards.map((card) => (
          <div key={card.id} className="summary-card">
            <div className="summary-card-top">
              <span className="summary-card-title">{card.title}</span>
              <div className="summary-card-icon">{card.icon}</div>
            </div>

            <div className="summary-card-body">
              <div className="summary-card-value">{card.value}</div>
              <span className={`summary-badge badge-${card.badgeType}`}>{card.badge}</span>
            </div>

            <div className="summary-card-footer">
              <span className="summary-card-subtext">{card.subtext}</span>
              <button
                type="button"
                className="summary-card-action"
                onClick={() => onNavigate(card.tabTarget)}
              >
                {card.actionLabel}
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
