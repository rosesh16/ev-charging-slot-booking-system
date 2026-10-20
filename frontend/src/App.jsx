import { useState, useCallback } from "react";
import "./App.css";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/useAuth";
import Sidebar from "./components/Sidebar";
import TopNav from "./components/TopNav";
import SummaryCards from "./components/SummaryCards";
import StationDiscovery from "./components/StationDiscovery";
import BookingsSection from "./components/BookingsSection";
import VehiclesView from "./components/VehiclesView";
import AuthModal from "./components/AuthModal";

function DashboardApp() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStationForBooking, setSelectedStationForBooking] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState("login");

  // Track live stations and chargers loaded from DRF
  const [liveStations, setLiveStations] = useState(null);

  // Track live private vehicle and booking counts for authenticated driver
  const [liveVehiclesCount, setLiveVehiclesCount] = useState(null);
  const [liveBookingsCount, setLiveBookingsCount] = useState(null);

  const { isAuthenticated, user } = useAuth();

  // Purely derived private driver metrics
  const displayedVehiclesCount = isAuthenticated ? liveVehiclesCount : null;
  const displayedBookingsCount = isAuthenticated ? liveBookingsCount : null;

  const handleStationsLoaded = useCallback((data) => {
    setLiveStations(data);
  }, []);

  const handleVehiclesUpdated = useCallback((vehicles) => {
    setLiveVehiclesCount(vehicles.length);
  }, []);

  const handleBookingsUpdated = useCallback((bookings) => {
    const activeCount = bookings.filter((b) => b.status === "CONFIRMED").length;
    setLiveBookingsCount(activeCount);
  }, []);

  const liveStationsCount = liveStations ? liveStations.length : null;
  const liveChargersCount = liveStations
    ? liveStations.reduce((sum, s) => sum + (s.chargers ? s.chargers.length : 0), 0)
    : null;

  const handleOpenAuth = (mode = "login") => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  };

  const handleSelectStationForBooking = (station) => {
    setSelectedStationForBooking(station);
    setActiveTab("bookings");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="volt-dashboard-root">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
        onOpenAuth={handleOpenAuth}
      />

      {/* Main Content Area */}
      <div className="volt-main-layout">
        {/* Top Navigation */}
        <TopNav
          activeTab={activeTab}
          onOpenMobile={() => setIsMobileOpen(true)}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onOpenAuth={handleOpenAuth}
        />

        {/* Dynamic Views */}
        <main className="dashboard-content-area">
          {activeTab === "dashboard" && (
            <div className="tab-view-container">
              <SummaryCards
                onNavigate={(tab) => setActiveTab(tab)}
                liveStationsCount={liveStationsCount}
                liveChargersCount={liveChargersCount}
                liveVehiclesCount={displayedVehiclesCount}
                liveBookingsCount={displayedBookingsCount}
                isAuthenticated={isAuthenticated}
              />
              <StationDiscovery
                searchQuery={searchQuery}
                onSelectStationForBooking={handleSelectStationForBooking}
                onStationsLoaded={handleStationsLoaded}
              />
              <BookingsSection
                selectedStationForBooking={selectedStationForBooking}
                stations={liveStations || []}
                onSelectStation={handleSelectStationForBooking}
                onOpenAuth={handleOpenAuth}
                onNavigate={(tab) => setActiveTab(tab)}
                onBookingsUpdated={handleBookingsUpdated}
              />
            </div>
          )}

          {activeTab === "stations" && (
            <div className="tab-view-container">
              <StationDiscovery
                searchQuery={searchQuery}
                onSelectStationForBooking={handleSelectStationForBooking}
                onStationsLoaded={handleStationsLoaded}
              />
            </div>
          )}

          {activeTab === "vehicles" && (
            <div className="tab-view-container">
              <VehiclesView
                onOpenAuth={handleOpenAuth}
                onVehiclesUpdated={handleVehiclesUpdated}
              />
            </div>
          )}

          {activeTab === "bookings" && (
            <div className="tab-view-container">
              <BookingsSection
                selectedStationForBooking={selectedStationForBooking}
                stations={liveStations || []}
                onSelectStation={handleSelectStationForBooking}
                onOpenAuth={handleOpenAuth}
                onNavigate={(tab) => setActiveTab(tab)}
                onBookingsUpdated={handleBookingsUpdated}
              />
            </div>
          )}
        </main>

        {/* Global Footer */}
        <footer className="dashboard-footer">
          <div className="footer-left">
            <span>VoltSlot &bull; EV Charging Slot Booking System</span>
            <span className="footer-divider">&bull;</span>
            <span className="footer-badge">develop branch</span>
            <span className="footer-divider">&bull;</span>
            <span className="footer-badge">
              {isAuthenticated && user
                ? `Signed In as ${user.username} (${user.role || "DRIVER"})`
                : "Guest Session"}
            </span>
          </div>
          <div className="footer-right">
            <span>Live APIs Connected &bull; Auth &amp; Booking Integrations Active</span>
          </div>
        </footer>
      </div>

      {/* Authentication Modal */}
      <AuthModal
        key={`${authModalOpen}-${authModalMode}`}
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <DashboardApp />
    </AuthProvider>
  );
}
