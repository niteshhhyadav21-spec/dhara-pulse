import { useState, useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "./App.css";

function getRainfallStatus(value) {
  if (value >= 50) return "Very High";
  if (value >= 20) return "High";
  if (value >= 5) return "Moderate";
  return "Low";
}

function getSoilStatus(value) {
  if (value >= 80) return "Very High";
  if (value >= 65) return "Elevated";
  if (value >= 50) return "Moderate";
  return "Low";
}

function getSlopeStatus(value) {
  if (value >= 35) return "Very Steep";
  if (value >= 25) return "Steep";
  if (value >= 15) return "Moderate";
  return "Gentle";
}

function getHistoricalStatus(value) {
  if (value >= 10) return "High";
  if (value >= 5) return "Present";
  if (value > 0) return "Limited";
  return "None";
}
function getRiskWarning(level) {
  switch (level) {
    case "CRITICAL":
      return {
        icon: "🚨",
        title: "Critical landslide risk conditions detected",
        message:
          "Multiple environmental indicators are currently contributing strongly to the system risk estimate.",
      };

    case "HIGH":
      return {
        icon: "⚠️",
        title: "High landslide risk conditions detected",
        message:
          "Several environmental indicators are elevated and require increased monitoring.",
      };

    case "MODERATE":
      return {
        icon: "⚠️",
        title: "Moderate landslide risk conditions detected",
        message:
          "Some environmental indicators are elevated and should continue to be monitored.",
      };

    case "LOW":
      return {
        icon: "ℹ️",
        title: "Low landslide risk conditions detected",
        message:
          "Current environmental indicators are within the lower range of the prototype risk model.",
      };

    default:
      return {
        icon: "⏳",
        title: "Calculating risk",
        message:
          "Dhara Pulse is collecting environmental data for this location.",
      };
  }
}
function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [language, setLanguage] = useState("English");
  const [showReport, setShowReport] = useState(false);
  const [risk, setRisk] = useState(null);
  const [weather, setWeather] = useState(null);
  const [soilMoisture, setSoilMoisture] = useState(null);
  const [soilHistory, setSoilHistory] = useState([]);
  const [historicalEvents, setHistoricalEvents] = useState(0);
  const [gsiLandslides, setGsiLandslides] = useState([]);
  const previousRiskLevel = useRef(null);
  const [alerts, setAlerts] = useState([]);
  const [reportType, setReportType] = useState("Landslide");
  const [reportLocation, setReportLocation] = useState("");
  const [reportDescription, setReportDescription] = useState("");
  const [selectedLocation, setSelectedLocation] = useState({
  lat: 26.14,
  lon: 91.74
  });
  const [reports, setReports] = useState([]);
 // ==========================================
// VERIFY / REJECT CITIZEN REPORT
// ==========================================

const updateReportStatus = async (reportId, newStatus) => {
  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/reports/${reportId}/status?status=${newStatus}`,
      {
        method: "PATCH"
      }
    );

    if (!response.ok) {
      throw new Error("Failed to update report status");
    }

    const data = await response.json();

    console.log("REPORT STATUS UPDATED:", data);

    // Refresh reports from database
    const reportsResponse = await fetch(
      "http://127.0.0.1:8000/api/reports"
    );

    const reportsData = await reportsResponse.json();

    setReports(reportsData.reports || []);

  } catch (error) {
    console.error("REPORT STATUS ERROR:", error);
    alert("Failed to update report status.");
  }
};






  useEffect(() => {
  const fetchReports = async () => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/reports"
      );

      if (!response.ok) {
        throw new Error("Failed to fetch reports");
      }

      const data = await response.json();

      console.log("CITIZEN REPORTS:", data);

      setReports(data.reports || []);

    } catch (error) {
      console.error("REPORT FETCH ERROR:", error);
    }
  };

  fetchReports();
}, []);
    const dataCards = [
    {
      icon: "🌧️",
      title: "Rainfall",
      value: weather?.rainfall_24h ?? 0,
      unit: "mm / 24h",
      status: "Live Weather"
    },
    {
      icon: "💧",
      title: "Soil Moisture",
      value: soilMoisture?.soil_moisture ?? 0,
      unit: "%",
      status: "Sensor Network"
    },
    {
      icon: "🏔️",
      title: "Slope",
      value:risk?.factors?.slope ?? 0,
      unit: "°",
      status: "Live Terrain Data"
    },
    {
      icon: "🏔️",
      title: "Landslides",
      value: historicalEvents,
      unit: "records",
      status: "Historical Data"
    },
  ];

useEffect(() => {

  async function loadLiveData() {
    try {

      // =========================
      // 1. WEATHER / RAINFALL
      // =========================
      const weatherResponse = await fetch(
        `http://127.0.0.1:8000/api/weather?lat=${selectedLocation.lat}&lon=${selectedLocation.lon}`
      );

      if (!weatherResponse.ok) {
        throw new Error("Weather API failed");
      }

      const weatherData = await weatherResponse.json();

      setWeather(weatherData);

      console.log("LIVE WEATHER DATA:", weatherData);


      // =========================
      // 2. SOIL MOISTURE
      // =========================
      const soilResponse = await fetch(
        "http://127.0.0.1:8000/api/soil-moisture"
      );

      if (!soilResponse.ok) {
        throw new Error("Soil Moisture API failed");
      }

      const soilData = await soilResponse.json();

      setSoilMoisture(soilData);

      console.log("LIVE SOIL MOISTURE:", soilData);




      // =========================
      // SOIL MOISTURE TREND
      // =========================

      const soilHistoryResponse = await fetch(
        "http://127.0.0.1:8000/api/soil-moisture/history"
      );

      if (!soilHistoryResponse.ok) {
        throw new Error("Soil Moisture History API failed");
      }

      const soilHistoryData = await soilHistoryResponse.json();
      setSoilHistory(soilHistoryData.readings || []);
      const readings = soilHistoryData.readings || [];

      let soilTrend = "STABLE";

      if (readings.length >= 2) {
        const latest = readings[0].soil_moisture;
        const previous = readings[1].soil_moisture;

        if (latest > previous + 2) {
          soilTrend = "RISING";
        } else if (latest < previous - 2) {
          soilTrend = "FALLING";
        }
      }

      console.log("SOIL MOISTURE TREND:", soilTrend);



      // TERRAIN / SLOPE
      const terrainResponse = await fetch(
        `http://127.0.0.1:8000/api/terrain?lat=${selectedLocation.lat}&lon=${selectedLocation.lon}`
       );

      if (!terrainResponse.ok) {
        throw new Error("Terrain API failed");
     }

      const terrainData = await terrainResponse.json();

      console.log("LIVE TERRAIN DATA:", terrainData);

      // HISTORICAL LANDSLIDES
      const historicalResponse = await fetch(
       `http://127.0.0.1:8000/api/gsi-historical-landslides/nearby?lat=${selectedLocation.lat}&lon=${selectedLocation.lon}&radius_km=50`
    );

      if (!historicalResponse.ok) {
       throw new Error("GSI Historical API failed");
  }

       const historicalData = await historicalResponse.json();

       const historicalEvents = historicalData.historical_events; 

       setHistoricalEvents(historicalEvents);
       setGsiLandslides(historicalData.landslides || []);
       console.log(
        "GSI HISTORICAL EVENTS:",
        historicalEvents
      );

       console.log(
        "GSI LANDSLIDE RECORDS:", 
       historicalData.landslides
      
      );
      // =========================
      // 3. RISK CALCULATION
      // =========================

      const rainfall = weatherData.rainfall_24h;
      const soilMoistureValue = soilData.soil_moisture;

      // Temporary prototype values
      const slope = terrainData.slope;
     

      const riskResponse = await fetch(
         `http://127.0.0.1:8000/api/risk?rainfall=${rainfall}&soil_moisture=${soilMoistureValue}&slope=${slope}&historical_events=${historicalEvents}&soil_trend=${soilTrend}`
      );

      if (!riskResponse.ok) {
        throw new Error("Risk API failed");
      }

      const riskData = await riskResponse.json();

      setRisk(riskData);

      console.log("LIVE RISK DATA:", riskData);


      if (
  riskData.level !== previousRiskLevel.current &&
          (
    riskData.level === "HIGH" ||
    riskData.level === "CRITICAL"
  )
) {
  try {

    const alertUrl =
      `http://127.0.0.1:8000/api/alerts` +
      `?risk_level=${encodeURIComponent(riskData.level)}` +
      `&risk_score=${riskData.score}` +
      `&latitude=${selectedLocation.lat}` +
      `&longitude=${selectedLocation.lon}` +
      `&message=${encodeURIComponent(riskData.explanation || "")}`;

    await fetch(alertUrl, {
      method: "POST"
    });

    console.log("🚨 ALERT SAVED:", riskData.level);
  } catch (error) {
    console.error("ALERT SAVE ERROR:", error);
  }
}

previousRiskLevel.current = riskData.level;
    } catch (error) {

      console.error("LIVE DATA ERROR:", error);

    }
  }


  // Load immediately
  loadLiveData();


  // Refresh every 30 seconds
  const interval = setInterval(loadLiveData, 30000);


  // Cleanup timer
  return () => clearInterval(interval);

}, [selectedLocation]);
  // =========================
// ALERT HISTORY
// =========================
useEffect(() => {
  async function loadAlerts() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/alerts"
      );

      if (!response.ok) {
        throw new Error("Failed to fetch alerts");
      }

      const data = await response.json();

      console.log("ALERT HISTORY:", data);

      setAlerts(data.alerts || []);
    } catch (error) {
      console.error("ALERT HISTORY ERROR:", error);
    }
  }

  // Load alerts immediately
  loadAlerts();

  // Refresh alerts every 10 seconds
  const interval = setInterval(() => {
    loadAlerts();
  }, 10000);

  // Stop the timer when the component is removed
  return () => {
    clearInterval(interval);
  };
}, []);
  const menu = [
    ["Dashboard", "⌂"],
    ["Risk Map", "🗺️"],
    ["Live Monitoring", "📡"],
    ["Citizen Reports", "📍"],
    ["Alerts", "🔔"],
    ["Authority Panel", "🏛️"],
  ];

  return (
    <div className="app">

      {/* SIDEBAR */}
      <aside className="sidebar">

        <div className="brand">
          <div className="brand-icon">💧</div>
          <div>
            <h1>Dhara Pulse</h1>
            <span>EARLY-WARNING • SAFETY • CARE</span>
          </div>
        </div>

        <div className="network">
          <span className="live-dot"></span>
          Live Network
        </div>

        <nav>
          {menu.map(([name, icon]) => (
            <button
              key={name}
              className={activePage === name ? "menu active" : "menu"}
              onClick={() => setActivePage(name)}
            >
              <span>{icon}</span>
              {name}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">

          <div className="offline-card">
            <div>📡</div>
            <div>
              <strong>Network Ready</strong>
              <small>Offline sync enabled</small>
            </div>
          </div>

          <button className="emergency-button">
            🚨 Emergency Help
          </button>

        </div>
      </aside>

      {/* MAIN */}
      <main className="main">

        {/* TOP BAR */}
        <header className="topbar">
          <div>
            <p className="eyebrow">
              INDIA DISASTER EARLY-WARNING PLATFORM
            </p>
            <h2>{activePage}</h2>
          </div>

          <div className="top-actions">

            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option>English</option>
              <option>Hindi</option>
              <option>Assamese</option>
              <option>Bengali</option>
            </select>

            <button className="icon-button">
              🔔
            </button>

            <div className="profile">
              <div className="avatar">DP</div>
              <div>
                <strong>Field User</strong>
                <small>Public Dashboard</small>
              </div>
            </div>

          </div>
        </header>

{activePage === "Alerts" && (
  <section className="sources-card" style={{ marginTop: "20px" }}>
    <div className="section-title">
      <div>
        <span className="small-label">
          ALERT HISTORY
        </span>

        <h3>
          Risk Alerts
        </h3>
      </div>

      <span className="data-status">
        ● {alerts.length} Alerts
      </span>
    </div>

    {alerts.length === 0 ? (
      <p style={{ padding: "20px" }}>
        No alerts found.
      </p>
    ) : (
      alerts.map((alert) => (
        <div
          key={alert.id}
          className="incident"
          style={{ marginTop: "12px" }}
        >
          <div className="incident-icon">
            {alert.risk_level === "CRITICAL"
              ? "🚨"
              : alert.risk_level === "HIGH"
              ? "⚠️"
              : "🟡"}
          </div>

          <div className="incident-info">
            <strong
                style={{
                    color:
                       alert.risk_level === "HIGH" ||
                       alert.risk_level === "CRITICAL"
                          ? "#d32f2f"
                          : alert.risk_level === "MODERATE"
                           ? "#d99a00"
                          : "#4f7cac"
                        
                          }}
            >
                {alert.risk_level} RISK
             </strong>

            <span>
              Risk Score: {alert.risk_score}
            </span>

            <span>
              Location: {alert.latitude.toFixed(4)},{" "}
              {alert.longitude.toFixed(4)}
            </span>
          </div>

          <div>
            <small>
              {alert.created_at}
            </small>
          </div>
        </div>
      ))
    )}
  </section>
)}
 {/* AUTHORITY PANEL */}

{activePage === "Authority Panel" && (
  <section
    className="sources-card"
    style={{ marginTop: "20px" }}
  >

    {/* PANEL HEADER */}

    <div className="section-title">
      <div>
        <span className="small-label">
          AUTHORITY CONTROL CENTER
        </span>

        <h3>Authority Panel</h3>
      </div>

      <span className="data-status">
        LIVE MONITORING
      </span>
    </div>

    <div style={{ padding: "20px" }}>

      <p style={{ marginBottom: "20px" }}>
        Real-time overview of environmental risk,
        alerts, citizen reports and historical activity.
      </p>

      {/* KPI CARDS */}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "12px"
        }}
      >

        {/* CURRENT RISK */}

        <div
          style={{
            padding: "16px",
            border: "1px solid #e5e7eb",
            borderRadius: "12px",
            background: "#ffffff"
          }}
        >
          <span className="small-label">
            CURRENT RISK
          </span>

          <h2>{risk?.score ?? "--"}</h2>

          <span>
            {risk?.level ?? "CALCULATING"}
          </span>
        </div>


        {/* HIGH / CRITICAL ALERTS */}

        <div
          style={{
            padding: "16px",
            border: "1px solid #e5e7eb",
            borderRadius: "12px",
            background: "#ffffff"
          }}
        >
          <span className="small-label">
            HIGH / CRITICAL ALERTS
          </span>

          <h2>
            {
              alerts.filter(
                (alert) =>
                  alert.risk_level === "HIGH" ||
                  alert.risk_level === "CRITICAL"
              ).length
            }
          </h2>

          <span>
            Requires attention
          </span>
        </div>


        {/* CITIZEN REPORTS */}

        <div
          style={{
            padding: "16px",
            border: "1px solid #e5e7eb",
            borderRadius: "12px",
            background: "#ffffff"
          }}
        >
          <span className="small-label">
            CITIZEN REPORTS
          </span>

          <h2>
            {reports.length}
          </h2>

          <span>
            Reports received
          </span>
        </div>


        {/* HISTORICAL LANDSLIDES */}

        <div
          style={{
            padding: "16px",
            border: "1px solid #e5e7eb",
            borderRadius: "12px",
            background: "#ffffff"
          }}
        >
          <span className="small-label">
            HISTORICAL LANDSLIDES
          </span>

          <h2>
            {gsiLandslides.length}
          </h2>

          <span>
            Nearby GSI records
          </span>
        </div>

      </div>


      {/* RECENT RISK ALERTS */}

      <div
        style={{
          marginTop: "25px",
          padding: "20px",
          border: "1px solid #e5e7eb",
          borderRadius: "12px",
          background: "#ffffff"
        }}
      >

        <div className="section-title">

          <div>
            <span className="small-label">
              RECENT RISK ALERTS
            </span>

            <h3>
              Latest Alerts
            </h3>
          </div>

          <span className="data-status">
            ● LIVE
          </span>

        </div>


        {alerts.length === 0 ? (

          <p style={{ marginTop: "15px" }}>
            No risk alerts available.
          </p>

        ) : (

          alerts.slice(0, 5).map((alert) => (

            <div
              className="incident"
              key={alert.id}
              style={{ marginTop: "12px" }}
            >

              <div className="incident-icon">
                {alert.risk_level === "CRITICAL"
                  ? "🚨"
                  : alert.risk_level === "HIGH"
                  ? "⚠️"
                  : "🟡"}
              </div>


              <div className="incident-info">

                <strong
                  style={{
                    color:
                      alert.risk_level === "CRITICAL"
                        ? "#b91c1c"
                        : alert.risk_level === "HIGH"
                        ? "#d32f2f"
                        : "#d99a00"
                  }}
                >
                  {alert.risk_level} RISK
                </strong>

                <span>
                  Risk Score: {alert.risk_score}
                </span>

                <span>
                  Location:{" "}
                  {Number(alert.latitude).toFixed(4)},{" "}
                  {Number(alert.longitude).toFixed(4)}
                </span>

                <small>
                  {alert.message || "Risk condition detected"}
                </small>

              </div>


              <div>
                <small>
                  {alert.created_at}
                </small>
              </div>

            </div>

          ))

        )}

      </div>


      {/* CITIZEN REPORTS */}

      <div
        style={{
          marginTop: "20px",
          padding: "20px",
          border: "1px solid #e5e7eb",
          borderRadius: "12px",
          background: "#ffffff"
        }}
      >

        <div className="section-title">

          <div>
            <span className="small-label">
              CITIZEN REPORTS
            </span>

            <h3>
              Latest Field Reports
            </h3>
          </div>

          <span className="data-status">
            ● {reports.length} REPORTS
          </span>

        </div>


        {reports.length === 0 ? (

          <p style={{ marginTop: "15px" }}>
            No citizen reports available.
          </p>

        ) : (

          reports.slice(0, 5).map((report) => (

            <div
              className="incident"
              key={report.id}
              style={{ marginTop: "12px" }}
            >

              <div className="incident-icon">
                📍
              </div>


              <div className="incident-info">

                <strong>
                  {report.hazard_type}
                </strong>

                <span>
                  {report.description ||
                    "No description provided"}
                </span>

                <span>
                  Location:{" "}
                  {Number(report.latitude).toFixed(4)},{" "}
                  {Number(report.longitude).toFixed(4)}
                </span>

              </div>


              <div
  style={{
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    gap: "8px"
  }}
>
  <span className="severity moderate">
    {report.status}
  </span>

  <small>
    Citizen Report
  </small>

  {report.status === "NEW" && (
    <div
      style={{
        display: "flex",
        gap: "6px",
        marginTop: "6px"
      }}
    >

      <button
        onClick={() =>
          updateReportStatus(report.id, "VERIFIED")
        }
        style={{
          padding: "6px 10px",
          border: "none",
          borderRadius: "6px",
          background: "#718d78",
          color: "white",
          cursor: "pointer",
          fontSize: "12px"
        }}
      >
        ✓ Verify
      </button>

      <button
        onClick={() =>
          updateReportStatus(report.id, "REJECTED")
        }
        style={{
          padding: "6px 10px",
          border: "none",
          borderRadius: "6px",
          background: "#b96f63",
          color: "white",
          cursor: "pointer",
          fontSize: "12px"
        }}
      >
        ✕ Reject
      </button>

    </div>
  )}
</div>
            </div>

          ))

        )}

      </div>

    </div>

  </section>
)}
        {/* LOCATION */}
        <section className="location-row">

          <div>
            <span className="small-label">
              MONITORING REGION
            </span>

            <h3>
              North Eastern Region, India
            </h3>

            <p>
              Assam • Meghalaya • Mizoram • Nagaland • Manipur • Tripura • Arunachal Pradesh • Sikkim
            </p>
          </div>

          <button className="location-button">
            📍 Use My Location
          </button>

        </section>

        {/* DYNAMIC ALERT */}

<section className="alert-banner">

  <div className="alert-icon">
    {getRiskWarning(risk?.level).icon}
  </div>

  <div className="alert-content">

    <span>
      SYSTEM RISK ESTIMATE • NOT AN OFFICIAL ALERT
    </span>

    <strong>
      {getRiskWarning(risk?.level).title}
    </strong>

    <small>
      {getRiskWarning(risk?.level).message}
    </small>

  </div>

  <span className="alert-status">
    {risk ? risk.level : "CALCULATING"}
  </span>

</section>
        {/* RISK + MAP */}
        <section className="hero-grid">

          {/* RISK CARD */}
          <div className="risk-card">

            <div className="card-header">

              <div>
                <span className="small-label">
                  LANDSLIDE RISK
                </span>

                <h3>
                  Current Risk Assessment
                </h3>
              </div>

              <span className="demo-tag">
                LIVE
              </span>

            </div>

            <div className="risk-score">

              <div className="score">
                 {risk ? risk.score : "--"}
              </div>

              <div>
                <strong>
                  {risk ? risk.level : "CALCULATING"}
                </strong>

                <span>
                  Risk Score / 100
                </span>
              </div>

            </div>

            <div className="risk-bar">

              <div
                style={{
                  width: `${risk ? risk.score : 0}%`
                }}
              ></div>

            </div>

            <div className="risk-scale">
              <span>LOW</span>
              <span>MODERATE</span>
              <span>HIGH</span>
              <span>CRITICAL</span>
            </div>

            <div className="risk-factors">

              <div>
                <span>🌧️ Rainfall</span>
                <strong>
                   {risk
                      ? getRainfallStatus(risk.factors.rainfall)
                      : "Calculating"}
                </strong>
              </div>

              <div>
                <span>💧 Soil Moisture</span>
                <strong>
                   {risk
                     ? getSoilStatus(risk.factors.soil_moisture)
                     : "Calculating"}
                </strong>
              </div>

              <div>
                <span>⛰️ Slope</span>
                <strong> 
                  {risk
                     ? getSlopeStatus(risk.factors.slope)
                     : "Calculating"}
                </strong>
              </div>

              <div>
                <span>📚 Historical Events</span>
                <strong> 
                  {risk
                     ? getHistoricalStatus(risk.factors.historical_events)
                     : "Calculating"}
                </strong>
              </div>

            </div>

            {/* RISK CONTRIBUTION BREAKDOWN */}
            <div
              style={{
                marginTop: "20px",
                paddingTop: "18px",
                borderTop: "1px solid rgba(255,255,255,0.08)"
            }}
            >

              <span className="small-label">
                RISK CONTRIBUTION
              </span>
  
              <div style={{ marginTop: "12px" }}>
              
                <div style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "8px"
                }}>
                  <span>🌧️Rainfall</span>
                  <span>
                    {risk?.factor_scores?.rainfall ?? "--"} / 35
                  </span>
                </div>

                <div style={{
                   display: "flex",
                   justifyContent: "space-between",
                   marginBottom: "8px"
                }}>
                  <span>💧Soil Moisture</span>
                  <strong>
                      {risk?.factor_scores?.soil_moisture ?? "--"} / 25
                  </strong>
                </div>
              
                <div style={{
                   display: "flex",
                   justifyContent: "space-between",
                   marginBottom: "8px"
                }}>
                  <span>⛰️Slope</span>
                  <strong>
                      {risk?.factor_scores?.slope ?? "--"} / 25
                  </strong>
                </div>
                
                <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                  }}>

                  <span>📚Historical Events</span>
                  <strong>
                      {risk?.factor_scores?.historical_events ?? "--"} / 15
                  </strong>
                </div>
              </div>
            </div>
          {/* RISK EXPLANATION */}
        <div
          style={{
            marginTop: "18px",
            padding: "14px",
            borderRadius: "10px",
            background: "rgba(255,255,255,0.04)"
       
          }}
       >

          <span className="small-label">
             WHY THIS RISK?
          </span>
         
         
          <p style={{ marginTop: "8px", lineHeight: "1.5" }}>
              {risk?.explanation ??
                  "Risk explanation will appear when live data is available."}
          </p>

        </div>


        <p className="disclaimer">
             Prototype risk estimate. Model calibration
             requires validated historical and sensor data.
        </p>
      </div>

          {/* MAP */}
          <div className="map-card">

            <div className="map-header">

              <div>
                <span className="small-label">
                  GEOSPATIAL MONITORING
                </span>

                <h3>
                  Risk Map
                </h3>
              </div>

              <span className="demo-tag">
                GIS
              </span>

            </div>

            <RiskMap 
            onLocationSelect={setSelectedLocation} 
            gsiLandslides={gsiLandslides}
            risk={risk}
            selectedLocation={selectedLocation}
            reports={reports}
            />

          </div>

        </section>

        {/* ENVIRONMENT */}
        <section>

          <div className="section-title">

            <div>
              <span className="small-label">
                ENVIRONMENTAL SIGNALS
              </span>

              <h3>
                Live Monitoring Inputs
              </h3>
            </div>

            <span className="data-status">
              ● Data pipeline ready
            </span>

          </div>

          <div className="data-grid">

            {dataCards.map((card) => (

              <div
                className="data-card"
                key={card.title}
              >

                <div className="data-icon">
                  {card.icon}
                </div>

                <div>

                  <span>
                    {card.title}
                  </span>

                  <div className="data-value">
                    {card.value}
                    <small>
                      {card.unit}
                    </small>
                  </div>

                  <p>
                    {card.status}
                  </p>

                </div>

              </div>

            ))}

          </div>

        </section>

        {/* DATA SOURCES */}
        <section className="sources-card">

          <div className="section-title">

            <div>
              <span className="small-label">
                DATA PIPELINE
              </span>

              <h3>
                Monitoring Sources
              </h3>
            </div>

          </div>

          <div className="source-grid">

            <Source
              icon="🌧️"
              title="Rainfall"
              text="Weather / rainfall API"
            />

            <Source
              icon="💧"
              title="Soil Moisture"
              text="IoT sensor network"
            />

            <Source
              icon="🛰️"
              title="Satellite"
              text="Satellite imagery"
            />

            <Source
              icon="⛰️"
              title="Terrain"
              text="Elevation + slope"
            />

            <Source
              icon="📚"
              title="Historical Data"
              text="Past landslide records"
            />

            <Source
              icon="📍"
              title="Citizen Reports"
              text="GPS + photo reports"
            />

          </div>

        </section>

        {/* REPORT + INCIDENTS */}
        <section className="bottom-grid">

          <div className="report-card">

            <span className="small-label">
              FIELD REPORTING
            </span>

            <h3>
              See Something? Report It.
            </h3>

            <p>
              Citizens and field teams can submit
              geo-tagged landslide, flood and road-blockage reports.
            </p>

            <button
              className="primary-button"
              onClick={() => setShowReport(true)}
            >
              📍 Report Hazard
            </button>

          </div>

          <div className="incidents-card">

            <div className="section-title">

              <div>
                <span className="small-label">
                  RECENT INCIDENTS
                </span>

                <h3>
                  Field Reports
                </h3>
              </div>

              <button className="text-button">
                View all →
              </button>

            </div>

            {reports.length === 0 ? (
  <p style={{ padding: "20px" }}>
    No citizen reports found.
  </p>
) : (
  reports.map((report) => (
    <div
      className="incident"
      key={report.id}
    >

      <div className="incident-icon">
        📍
      </div>

      <div className="incident-info">

        <strong>
          {report.hazard_type}
        </strong>

        <span>
          {report.description || "No description provided"}
        </span>

        <small>
          Location: {Number(report.latitude).toFixed(4)},{" "}
          {Number(report.longitude).toFixed(4)}
        </small>

      </div>

      <div>

        <span className="severity moderate">
          {report.status}
        </span>

        <small>
          Citizen Report
        </small>

      </div>

    </div>
  ))
)}

          </div>

        </section>

        {/* EMERGENCY */}
        <section className="emergency-section">

          <div>

            <span className="small-label">
              SAFETY & PREPAREDNESS
            </span>

            <h3>
              Emergency Readiness
            </h3>

            <p>
              Keep essential information available
              even during low connectivity.
            </p>

          </div>

          <div className="emergency-actions">

            <button>
              📋 Safety Checklist
            </button>

            <button>
              📞 Emergency Contacts
            </button>

            <button>
              📴 Offline Mode
            </button>

          </div>

        </section>

        <footer>
          Dhara Pulse • Disaster Early-Warning & Monitoring Platform
        </footer>

      </main>

      {/* REPORT MODAL */}
      {showReport && (

        <div className="modal-overlay">

          <div className="modal">

            <button
              className="close"
              onClick={() => setShowReport(false)}
            >
              ×
            </button>

            <span className="small-label">
              CITIZEN REPORT
            </span>

            <h2>
              Report a Hazard
            </h2>

            <label>
              Hazard Type
            </label>

            <select

              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              <option>Landslide</option>
              <option>Flash Flood</option>
              <option>Heavy Rainfall</option>
              <option>Road Blockage</option>
              <option>Slope Failure</option>
            </select>

            <label>
              Location
            </label>

            <input
              value={reportLocation}
              onChange={(e) => setReportLocation(e.target.value)}
              placeholder="Enter location"
            />

            <label>
              Description
            </label>

            <textarea
              value={reportDescription}
              onChange={(e) => setReportDescription(e.target.value)}
               placeholder="Describe what you observed..."
            />

            <button
                className="primary-button full"
                onClick={async () => {
                  try {
                    const response = await fetch(
                       "http://127.0.0.1:8000/api/reports",
                      {
                         method: "POST",
                         headers: {
                           "Content-Type": "application/json"
                       },
                       body: JSON.stringify({
                         hazard_type: reportType,
                         description: reportDescription,
                         latitude: selectedLocation.lat,
                         longitude: selectedLocation.lon
                    })
                }
             );

      if (!response.ok) {
        throw new Error("Report submission failed");
      }

      const data = await response.json();

      
      console.log("REPORT SAVED:", data);

// Refresh citizen reports from database
const reportsResponse = await fetch(
  "http://127.0.0.1:8000/api/reports"
);

const reportsData = await reportsResponse.json();

console.log("UPDATED REPORTS:", reportsData);

setReports(reportsData.reports || []);

alert("Hazard report submitted successfully!");

setReportDescription("");
setReportLocation("");
setReportType("Landslide");
setShowReport(false);

    } catch (error) {
      console.error("REPORT ERROR:", error);
      alert("Failed to submit hazard report.");
    }
  }}
>
  Submit Report
</button>

          </div>

        </div>

      )}

    </div>
  );
}

function Source({ icon, title, text }) {
  return (
    <div className="source">

      <div>
        {icon}
      </div>

      <section>

        <strong>
          {title}
        </strong>

        <span>
          {text}
        </span>

      </section>

    </div>
  );
}

function RiskMap({ onLocationSelect, gsiLandslides, risk,selectedLocation, reports }) {

  const mapRef = useRef(null);
  const landslideLayerRef = useRef(null);
  const selectedMarkerRef = useRef(null);
  const riskZoneRef = useRef(null);
  const reportsLayerRef = useRef(null);

  // ==========================================
  // 1. CREATE MAP
  // ==========================================

  useEffect(() => {

    if (mapRef.current) return;

    const map = L
      .map("dhara-map")
      .setView([25.5, 91.5], 6);

    // OpenStreetMap
    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        attribution:
          "&copy; OpenStreetMap contributors",
      }
    ).addTo(map);


    // ==========================================
    // MAP CLICK
    // ==========================================

    map.on("click", (event) => {

      const { lat, lng } = event.latlng;

      console.log(
        "SELECTED LOCATION:",
        lat,
        lng
      );


      // Remove previous selected pointer
      if (selectedMarkerRef.current) {
        selectedMarkerRef.current.remove();
      }


      // Create new selected-location pointer
      const marker = L.marker([lat, lng])
  .addTo(map)
  .bindPopup(`
    <div style="min-width: 200px; font-family: Arial, sans-serif;">
      <strong style="font-size: 15px;">
        Dhara Pulse
      </strong>

      <hr style="margin: 8px 0;">

      <strong>Selected Location</strong><br><br>

      Latitude: ${lat.toFixed(5)}<br>
      Longitude: ${lng.toFixed(5)}<br><br>

      <span style="color: #666;">
        ⏳ Calculating live risk...
      </span>
    </div>
  `)
  .openPopup();


      // Save marker reference
      selectedMarkerRef.current = marker;


      // Send coordinates to App
      onLocationSelect({
        lat,
        lon: lng
      });

    });



    // Save map reference
    mapRef.current = map;


    // ==========================================
    // CLEANUP
    // ==========================================

    return () => {

      if (selectedMarkerRef.current) {
        selectedMarkerRef.current.remove();
        selectedMarkerRef.current = null;
      }

      map.remove();

      mapRef.current = null;

    };

  }, [onLocationSelect]);

// ==========================================
// 2. UPDATE SELECTED LOCATION WITH LIVE RISK
// ==========================================

useEffect(() => {
  if (!selectedMarkerRef.current || !risk || !selectedLocation) {
    return;
  }

  const marker = selectedMarkerRef.current;

  const riskColor =
    risk.level === "CRITICAL"
      ? "#8f3f3f"
      : risk.level === "HIGH"
      ? "#b96f63"
      : risk.level === "MODERATE"
      ? "#b49a63"
      : "#718d78";

  marker.bindPopup(`
    <div style="
      min-width: 220px;
      font-family: Arial, sans-serif;
    ">

      <div style="
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 8px;
      ">
        Dhara Pulse Risk
      </div>

      <div style="
        padding: 10px;
        border-radius: 8px;
        background: #f5f5f5;
        border-left: 5px solid ${riskColor};
        margin-bottom: 10px;
      ">

        <strong style="font-size: 15px;">
          ${risk.level}
        </strong>

        <br>

        <span>
          Risk Score: ${risk.score}/100
        </span>

      </div>

      <div style="
        font-size: 13px;
        line-height: 1.8;
      ">

        📍 Latitude:
        ${selectedLocation.lat.toFixed(5)}
        <br>

        📍 Longitude:
        ${selectedLocation.lon.toFixed(5)}
        <br><br>

        <strong>Risk Factors</strong>
        <br>

        🌧️ Rainfall:
        ${risk.factors?.rainfall ?? "N/A"}
        mm
        <br>

        💧 Soil Moisture:
        ${risk.factors?.soil_moisture ?? "N/A"}%
        <br>

        ⛰️ Slope:
        ${risk.factors?.slope ?? "N/A"}°
        <br>

        📚 Historical Events:
        ${risk.factors?.historical_events ?? "N/A"}

      </div>

      <hr style="margin: 10px 0;">

      <small style="color: #666;">
        Prototype risk estimate.
        <br>
        Not an official warning.
      </small>

    </div>
  `);

}, [risk, selectedLocation]);

  // ==========================================
// 2. DYNAMIC PROTOTYPE RISK ZONE
// ==========================================

useEffect(() => {
  if (!mapRef.current || !risk || !selectedLocation) return;

  // Remove previous risk zone
  if (riskZoneRef.current) {
    riskZoneRef.current.remove();
    riskZoneRef.current = null;
  }

  let zoneColor = "#718d78";
  let zoneFill = "#9fb79a";

  if (risk.level === "MODERATE") {
    zoneColor = "#b49a63";
    zoneFill = "#d9bb7c";
  }

  if (risk.level === "HIGH") {
    zoneColor = "#b96f63";
    zoneFill = "#d99b8c";
  }

  if (risk.level === "CRITICAL") {
    zoneColor = "#8f3f3f";
    zoneFill = "#d66b6b";
  }

  const riskZone = L.circle(
    [
      selectedLocation.lat,
      selectedLocation.lon
    ],
    {
      radius:
        risk.level === "CRITICAL"
          ? 50000
          : risk.level === "HIGH"
          ? 40000
          : risk.level === "MODERATE"
          ? 30000
          : 20000,

      color: zoneColor,
      fillColor: zoneFill,
      fillOpacity: 0.25,
      weight: 2
    }
  ).addTo(mapRef.current);

  riskZone.bindPopup(`
  <div style="min-width: 220px; font-family: Arial, sans-serif;">

    <div style="
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 10px;
    ">
      Dhara Pulse Risk Assessment
    </div>

    <div style="
      padding: 8px;
      border-radius: 8px;
      background: #f3f4f6;
      margin-bottom: 10px;
    ">
      <strong>Risk Level:</strong> ${risk.level}<br>
      <strong>Risk Score:</strong> ${risk.score}/100
    </div>

    <div style="font-size: 13px; line-height: 1.7;">

      <strong>Environmental Factors</strong><br>

      🌧️ Rainfall:
${risk.factors?.rainfall ?? "N/A"} mm / 24h
<br>

💧 Soil Moisture:
${risk.factors?.soil_moisture ?? "N/A"}%
<br>

⛰️ Slope:
${risk.factors?.slope ?? "N/A"}°
<br>

🏔️ Historical Events:
${risk.factors?.historical_events ?? "N/A"}
    </div>

    <hr style="margin: 10px 0;">

    <div style="
      font-size: 11px;
      color: #666;
      line-height: 1.4;
    ">
      Prototype risk estimate based on available
      environmental and historical data.
      <br>
      Not an official warning.
    </div>

  </div>
`);

  riskZoneRef.current = riskZone;

}, [risk, selectedLocation]);

  // ==========================================
  // 2. GSI HISTORICAL LANDSLIDE MARKERS
  // ==========================================

  useEffect(() => {

    if (!mapRef.current) return;


    // Remove old GSI layer
    if (landslideLayerRef.current) {

      landslideLayerRef.current.remove();

      landslideLayerRef.current = null;

    }


    const layer = L.layerGroup();


    // Add GSI landslide records
    gsiLandslides.forEach((landslide) => {

      if (
        landslide.latitude == null ||
        landslide.longitude == null
      ) {
        return;
      }


      const marker = L.circleMarker(
        [
          landslide.latitude,
          landslide.longitude
        ],
        {
          radius: 6,
          weight: 2,
          fillOpacity: 0.8,
        }
      );


      marker.bindPopup(`
        <strong>Historical Landslide</strong><br><br>

        <strong>State:</strong>
        ${landslide.state ?? "N/A"}<br>

        <strong>District:</strong>
        ${landslide.district ?? "N/A"}<br>

        <strong>Landslide:</strong>
        ${landslide.slide_name ?? "N/A"}<br>

        <strong>Year:</strong>
        ${landslide.year ?? "N/A"}<br>

        <strong>Material:</strong>
        ${landslide.material ?? "N/A"}<br>

        <strong>Movement:</strong>
        ${landslide.movement_type ?? "N/A"}<br>

        <strong>Distance:</strong>
        ${landslide.distance_km ?? "N/A"} km<br>

        <strong>Source:</strong>
        GSI Landslide Inventory
      `);


      marker.addTo(layer);

    });


    layer.addTo(mapRef.current);

    landslideLayerRef.current = layer;


  }, [gsiLandslides]);

// ==========================================
// 4. MAP LEGEND
// ==========================================

useEffect(() => {
  if (!mapRef.current) return;

  const legend = L.control({ position: "bottomright" });

  legend.onAdd = function () {
    const div = L.DomUtil.create(
      "div",
      "dhara-map-legend"
    );

    div.innerHTML = `
      <div style="
        background: white;
        padding: 10px 12px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-family: Arial, sans-serif;
        font-size: 12px;
        line-height: 1.8;
      ">

        <strong style="font-size: 13px;">
          MAP LEGEND
        </strong>

        <div>
          <span style="color:#718d78;">●</span>
          Low Risk Zone
        </div>

        <div>
          <span style="color:#b49a63;">●</span>
          Moderate Risk Zone
        </div>

        <div>
          <span style="color:#b96f63;">●</span>
          High Risk Zone
        </div>

        <div>
          <span style="color:#8f3f3f;">●</span>
          Critical Risk Zone
        </div>

        <div>
          <span style="color:#333;">●</span>
          Historical Landslide
        </div>

        <div>
          📍 Selected Location
        </div>

      </div>
    `;

    return div;
  };

  legend.addTo(mapRef.current);

  return () => {
    legend.remove();
  };

}, []);

// ==========================================
// 5. CITIZEN REPORT MARKERS
// ==========================================

useEffect(() => {
  if (!mapRef.current) return;

  // Remove previous citizen-report layer
  if (reportsLayerRef.current) {
    reportsLayerRef.current.remove();
    reportsLayerRef.current = null;
  }

  const layer = L.layerGroup();

  (reports || []).forEach((report) => {

    if (
      report.latitude == null ||
      report.longitude == null
    ) {
      return;
    }

   const reportStatus = String(
  report.status || "NEW"
).toUpperCase();

let markerColor = "#6b4fa1";
let markerFillColor = "#9b7bc4";

if (reportStatus === "VERIFIED") {
  markerColor = "#4f7c59";
  markerFillColor = "#718d78";
}

if (reportStatus === "REJECTED") {
  markerColor = "#777777";
  markerFillColor = "#aaaaaa";
}

const marker = L.circleMarker(
  [
    Number(report.latitude),
    Number(report.longitude)
  ],
  {
    radius: 7,
    color: markerColor,
    fillColor: markerFillColor,
    fillOpacity: 0.9,
    weight: 2
  }
);

    marker.bindPopup(`
      <div style="
        min-width: 210px;
        font-family: Arial, sans-serif;
      ">

        <strong style="font-size: 15px;">
          Citizen Hazard Report
        </strong>

        <hr style="margin: 8px 0;">

        <strong>Hazard:</strong>
        ${report.hazard_type ?? "Unknown"}
        <br>

       <strong>Status:</strong>
<span style="
  font-weight: 700;
  color: ${
    reportStatus === "VERIFIED"
      ? "#4f7c59"
      : reportStatus === "REJECTED"
      ? "#777777"
      : "#6b4fa1"
  };
">
  ${reportStatus}
</span>
        <br>

        <strong>Location:</strong>
        ${Number(report.latitude).toFixed(5)},
        ${Number(report.longitude).toFixed(5)}
        <br><br>

        <strong>Description:</strong><br>
        ${report.description || "No description provided"}

        <hr style="margin: 8px 0;">

        <small style="color:#666;">
          Source: Citizen Report
        </small>

      </div>
    `);

    marker.addTo(layer);
  });

  layer.addTo(mapRef.current);

  reportsLayerRef.current = layer;

}, [reports]);

  // ==========================================
  // MAP CONTAINER
  // ==========================================

  return (
    <div
      id="dhara-map"
      style={{
        height: "100%",
        width: "100%",
      }}
    ></div>
  );

}
export default App;