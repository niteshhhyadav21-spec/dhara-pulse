import React, { useState } from "react";
import "./Login.css";
import heroImage from "./assets/hero.png";

const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
];

function Login({ onLogin }) {
  const [isSignUp, setIsSignUp] = useState(true);

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    phone: "",
    location: "",
    state: "",
    city: "",
    alerts: false,
  });

  const [errors, setErrors] = useState({});
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationData, setLocationData] = useState(null);

  // ---------------------------------------
  // EMAIL
  // ---------------------------------------
  const handleEmailChange = (e) => {
    let value = e.target.value.toLowerCase();

    // User only types the part before @gmail.com
    value = value.replace(/@.*$/g, "");
    value = value.replace(/\s/g, "");

    setForm((prev) => ({
      ...prev,
      email: value,
    }));
  };

  // ---------------------------------------
  // PHONE
  // ---------------------------------------
  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 10);

    setForm((prev) => ({
      ...prev,
      phone: value,
    }));
  };

  // ---------------------------------------
  // PASSWORD
  // ---------------------------------------
  const getPasswordStrength = () => {
    const password = form.password;

    if (!password) {
      return {
        score: 0,
        text: "Password strength",
      };
    }

    let score = 0;

    // 1. Alphabet
    if (/[A-Za-z]/.test(password)) score++;

    // 2. Digit
    if (/\d/.test(password)) score++;

    // 3. Space
    if (/\s/.test(password)) score++;

    // 4. Special character
    if (/[^A-Za-z0-9\s]/.test(password)) score++;

    if (score === 1) {
      return { score: 1, text: "Weak" };
    }

    if (score === 2) {
      return { score: 2, text: "Fair" };
    }

    if (score === 3) {
      return { score: 3, text: "Good" };
    }

    return { score: 4, text: "Strong" };
  };

  const passwordStrength = getPasswordStrength();

  // ---------------------------------------
  // NORMAL INPUT
  // ---------------------------------------
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));

    // Remove red border when user starts correcting field
    setErrors((prev) => ({
      ...prev,
      [name]: false,
    }));
  };

  // ---------------------------------------
  // LIVE LOCATION
  // ---------------------------------------
  const detectLocation = () => {
    setErrors((prev) => ({
      ...prev,
      location: false,
    }));

    if (!navigator.geolocation) {
      setErrors((prev) => ({
        ...prev,
        location: true,
      }));
      return;
    }

    setLocationLoading(true);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const accuracy = position.coords.accuracy;

        const locationText =
          `GPS: ${lat.toFixed(5)}, ${lon.toFixed(5)}`;

        setForm((prev) => ({
          ...prev,
          location: locationText,
        }));

        setLocationData({
          lat,
          lon,
          accuracy,
        });

        setLocationLoading(false);
      },
      (error) => {
        console.error("LOCATION ERROR:", error);

        setLocationLoading(false);

        setErrors((prev) => ({
          ...prev,
          location: true,
        }));
      },
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 15000,
      }
    );
  };

  // ---------------------------------------
  // VALIDATE SIGN UP
  // ---------------------------------------
  const validateSignup = () => {
    const newErrors = {};

    if (!form.name.trim() || form.name.trim().length < 3) {
      newErrors.name = true;
    }

    // Automatic Gmail format
    const finalEmail = `${form.email.trim()}@gmail.com`;

    if (
      !form.email.trim() ||
      !/^[a-zA-Z0-9._%+-]+@gmail\.com$/.test(finalEmail)
    ) {
      newErrors.email = true;
    }

    // Password must contain at least 3 of:
    // alphabet, digit, space, special character
    if (passwordStrength.score < 3 || form.password.length < 6) {
      newErrors.password = true;
    }

    // Exactly 10 digits
    if (!/^\d{10}$/.test(form.phone)) {
      newErrors.phone = true;
    }

    // Location required
    if (!form.location.trim() || !locationData) {
      newErrors.location = true;
    }

    if (!form.state) {
      newErrors.state = true;
    }

    if (!form.city.trim()) {
      newErrors.city = true;
    }

    if (!form.alerts) {
      newErrors.alerts = true;
    }

    setErrors(newErrors);

    return Object.keys(newErrors).length === 0;
  };

  // ---------------------------------------
  // CREATE ACCOUNT
  // ---------------------------------------
  const handleSignup = (e) => {
    e.preventDefault();

    const valid = validateSignup();

    if (!valid) {
      return;
    }

    const finalEmail = `${form.email.trim()}@gmail.com`;

    const userData = {
      name: form.name.trim(),
      email: finalEmail,
      password: form.password,
      phone: `+91${form.phone}`,
      location: form.location,
      state: form.state,
      city: form.city.trim(),

      // VERY IMPORTANT:
      // Send GPS coordinates to App.jsx
      locationCoordinates: locationData,
    };

    console.log("DHARA PULSE USER:", userData);

    // Only after EVERYTHING is valid:
    onLogin(userData);
  };

  // ---------------------------------------
  // SIGN IN
  // ---------------------------------------
  const handleSignin = (e) => {
    e.preventDefault();

    const email = e.target.loginEmail.value.trim();
    const password = e.target.loginPassword.value;

    const newErrors = {};

    if (!email) {
      newErrors.loginEmail = true;
    }

    if (!password) {
      newErrors.loginPassword = true;
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length > 0) {
      return;
    }

    onLogin({
      email,
      password,
    });
  };

  return (
    <div className="login-page">

      {/* LEFT SIDE */}
      <div className="login-left">

        <div className="login-brand">

          <div className="login-logo">💧</div>

          <div>
            <h2>Dhara Pulse</h2>
            <p>EARLY-WARNING • SAFETY • CARE</p>
          </div>

          <div className="live-badge">
            <span></span>
            Live Network
          </div>

        </div>

        <div className="hero-image-container">
          <img
            src={heroImage}
            alt="Dhara Pulse safety monitoring"
            className="floating-hero"
          />
        </div>

        <div className="login-message">

          <h1>
            Gentle alerts,
            <br />
            stronger <span>communities.</span>
          </h1>

          <p>
            Dhara Pulse monitors weather and environmental
            conditions to help communities stay informed,
            prepared and safe.
          </p>

        </div>

        <div className="login-stats">

          <div>
            <strong>28+</strong>
            <span>STATES COVERED</span>
          </div>

          <div>
            <strong>4.2L</strong>
            <span>FAMILIES SAFE</span>
          </div>

          <div>
            <strong>~90s</strong>
            <span>ALERT SPEED</span>
          </div>

        </div>

      </div>


      {/* RIGHT SIDE */}
      <div className="login-right">

        <div className="login-card">

          <div className="welcome">

            <h1>
              {isSignUp
                ? "Welcome to safety"
                : "Welcome back"}
            </h1>

            <p>
              {isSignUp
                ? "Create your pulse profile to see your city's live condition."
                : "Sign in to monitor weather and safety conditions."}
            </p>

          </div>


          {/* SWITCH */}
          <div className="login-switch">

            <button
              type="button"
              className={isSignUp ? "active" : ""}
              onClick={() => {
                setIsSignUp(true);
                setErrors({});
              }}
            >
              Create Account
            </button>

            <button
              type="button"
              className={!isSignUp ? "active" : ""}
              onClick={() => {
                setIsSignUp(false);
                setErrors({});
              }}
            >
              Sign In
            </button>

          </div>


          {/* ================= SIGN UP ================= */}
          {isSignUp && (

            <form onSubmit={handleSignup}>

              <div className="input-row">

                <input
                  className={errors.name ? "input-error" : ""}
                  type="text"
                  name="name"
                  placeholder="Full name *"
                  value={form.name}
                  onChange={handleChange}
                />

                <div className="email-wrapper">
                  <input
                    className={errors.email ? "input-error" : ""}
                    type="text"
                    placeholder="Email address *"
                    value={form.email}
                    onChange={handleEmailChange}
                  />

                  <span className="email-suffix">
                    @gmail.com
                  </span>
                </div>

              </div>


              <div className="input-row">

                <div className="password-wrapper">

                  <input
                    className={errors.password ? "input-error" : ""}
                    type="password"
                    name="password"
                    placeholder="Password *"
                    value={form.password}
                    onChange={handleChange}
                  />

                  <span
                    className={`password-strength strength-${passwordStrength.score}`}
                  >
                    {passwordStrength.text}
                  </span>

                </div>


                <div className="phone-wrapper">

                  <span className="country-code">
                    +91
                  </span>

                  <input
                    className={errors.phone ? "input-error" : ""}
                    type="tel"
                    inputMode="numeric"
                    maxLength={10}
                    placeholder="10-digit number *"
                    value={form.phone}
                    onChange={handlePhoneChange}
                  />

                </div>

              </div>


              {/* PASSWORD STRENGTH */}
              <div className="strength-container">

                <div className="strength-track">

                  <div
                    className="strength-fill"
                    style={{
                      width: `${passwordStrength.score * 25}%`,
                    }}
                  ></div>

                </div>

                <span>
                  {passwordStrength.text}
                </span>

              </div>


              {/* LOCATION */}
              <div className="location-row">

                <input
                  className={errors.location ? "input-error" : ""}
                  type="text"
                  name="location"
                  placeholder="Your location / area *"
                  value={form.location}
                  onChange={handleChange}
                />

                <button
                  type="button"
                  className="detect-button"
                  onClick={detectLocation}
                  disabled={locationLoading}
                >
                  {locationLoading
                    ? "Locating..."
                    : locationData
                    ? "✓ Found"
                    : "Detect"}
                </button>

              </div>


              {/* STATE + CITY */}
              <div className="input-row">

                <select
                  name="state"
                  className={errors.state ? "input-error" : ""}
                  value={form.state}
                  onChange={handleChange}
                >
                  <option value="">
                    Select state *
                  </option>

                  {INDIAN_STATES.map((state) => (
                    <option key={state} value={state}>
                      {state}
                    </option>
                  ))}

                </select>


                <input
                  className={errors.city ? "input-error" : ""}
                  type="text"
                  name="city"
                  placeholder="Your city *"
                  value={form.city}
                  onChange={handleChange}
                />

              </div>


              {/* ALERT AGREEMENT */}
              <label
                className={`alert-checkbox ${
                  errors.alerts ? "checkbox-error" : ""
                }`}
              >

                <input
                  type="checkbox"
                  name="alerts"
                  checked={form.alerts}
                  onChange={handleChange}
                />

                <span>
                  I agree to receive gentle SMS, WhatsApp & push
                  alerts for floods, storms, heatwaves & air quality
                  for my city & state.
                </span>

              </label>


              {/* SUBMIT */}
              <button
                type="submit"
                className="login-button"
              >
                🛡 Create Safe Account & View My City Status
              </button>


              <div className="demo-login">
                ✦ All fields are required to enter Dhara Pulse
              </div>

            </form>

          )}


          {/* ================= SIGN IN ================= */}
          {!isSignUp && (

            <form onSubmit={handleSignin}>

              <input
                className={`full-input ${
                  errors.loginEmail ? "input-error" : ""
                }`}
                name="loginEmail"
                type="email"
                placeholder="Registered email address"
              />

              <input
                className={`full-input ${
                  errors.loginPassword ? "input-error" : ""
                }`}
                name="loginPassword"
                type="password"
                placeholder="Password"
              />

              <div className="forgot">
                Forgot password?
              </div>

              <button
                type="submit"
                className="login-button"
              >
                Sign In to Dhara Pulse
              </button>

            </form>

          )}

        </div>

      </div>

    </div>
  );
}

export default Login;