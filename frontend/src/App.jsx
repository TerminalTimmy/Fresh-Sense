
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

const produceOptions = [
  { value: "apple", name: "Apple", emoji: "🍎" },
  { value: "banana", name: "Banana", emoji: "🍌" },
  { value: "orange", name: "Orange", emoji: "🍊" },
];

function App() {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [produceType, setProduceType] = useState("apple");
  const [temperature, setTemperature] = useState("20");
  const [humidity, setHumidity] = useState("60");
  const [storageDays, setStorageDays] = useState("2");
  const [storageEnvironment, setStorageEnvironment] = useState("");
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherMessage, setWeatherMessage] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fileInputRef = useRef(null);
  const previewUrlRef = useRef(null);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
      }
    };
  }, []);

  function handleImageChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("Please select an image smaller than 10 MB.");
      return;
    }

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
    }

    const url = URL.createObjectURL(file);
    previewUrlRef.current = url;
    setImage(file);
    setPreview(url);
    setResult(null);
    setError("");
  }

  async function fetchWeather() {
    if (!navigator.geolocation) {
      setWeatherMessage("Geolocation is unavailable on this device.");
      return;
    }

    setWeatherLoading(true);
    setWeatherMessage("");

    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const params = new URLSearchParams({
            latitude: String(coords.latitude),
            longitude: String(coords.longitude),
            current: "temperature_2m,relative_humidity_2m",
          });

          const response = await fetch(
            `https://api.open-meteo.com/v1/forecast?${params}`
          );

          if (!response.ok) {
            throw new Error("Weather service unavailable.");
          }

          const data = await response.json();
          const current = data.current;

          if (
            !Number.isFinite(current?.temperature_2m) ||
            !Number.isFinite(current?.relative_humidity_2m)
          ) {
            throw new Error("Weather readings unavailable.");
          }

          setWeather({
            temperature: current.temperature_2m,
            humidity: current.relative_humidity_2m,
            time: current.time,
          });

          setTemperature(String(current.temperature_2m));
          setHumidity(String(current.relative_humidity_2m));

          setWeatherMessage(
            "Outdoor weather loaded. Edit the values if your fruit is stored indoors."
          );
        } catch (err) {
          setWeatherMessage(err.message);
        } finally {
          setWeatherLoading(false);
        }
      },
      () => {
        setWeatherMessage(
          "Location unavailable or permission denied. Enter storage conditions manually."
        );
        setWeatherLoading(false);
      },
      { timeout: 12000, maximumAge: 300000 }
    );
  }

  async function handlePredict(event) {
    event.preventDefault();

    if (!image) {
      setError("Please scan or upload a fruit image.");
      return;
    }

    if (!API_URL) {
      setError("Backend API URL is not configured.");
      return;
    }

    const temp = Number(temperature);
    const humid = Number(humidity);
    const days = Number(storageDays);

    if (
      temperature.trim() === "" ||
      humidity.trim() === "" ||
      storageDays.trim() === "" ||
      !Number.isFinite(temp) ||
      !Number.isFinite(humid) ||
      !Number.isFinite(days) ||
      temp < -20 ||
      temp > 60 ||
      humid < 0 ||
      humid > 100 ||
      days < 0
    ) {
      setError("Please enter valid environmental conditions.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("image", image);
    formData.append("temperature", String(temp));
    formData.append("humidity", String(humid));
    formData.append("storage_days", String(days));
    formData.append("produce_type", produceType);
    if (storageEnvironment) {
      formData.append("storage_environment", storageEnvironment);
    }

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : `Prediction failed (HTTP ${response.status}).`
        );
      }

      setResult(await response.json());
    } catch (err) {
      setError(err.message || "Could not connect to the prediction API.");
    } finally {
      setLoading(false);
    }
  }

  const selectedProduce = produceOptions.find(
    (item) => item.value === produceType
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#home">
          <span className="brand-mark">✳</span>
          <span>FreshSense <strong>AI</strong></span>
        </a>
        <span className="topbar-tag">AI-powered produce insights</span>
      </header>

      <main id="home" className="dashboard">
        <section className="hero">
          <div>
            <span className="eyebrow">SMART AGRICULTURE • FRESHER FUTURES</span>
            <h1>Know your produce.<br /><em>Keep it fresher.</em></h1>
            <p>
              Scan your fruit, check its visual freshness, and explore
              how storage conditions may affect its remaining life.
            </p>
            <a className="hero-link" href="#scanner">
              Start scanning <span aria-hidden="true">↗</span>
            </a>
          </div>
          <div className="hero-art" aria-hidden="true">
            <span>🍎</span><span>🍊</span><span>🍌</span>
          </div>
        </section>

        <div className="workspace">
          <section className="panel scanner-panel" id="scanner">
            <div className="section-heading">
              <div>
                <span className="eyebrow">01 / IMAGE ANALYSIS</span>
                <h2>Scan your produce</h2>
              </div>
              <span className="section-icon">◎</span>
            </div>

            <form onSubmit={handlePredict}>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleImageChange}
                className="visually-hidden"
                id="fruit-image"
              />

              <div className="upload-zone">
                {preview ? (
                  <img src={preview} alt="Selected fruit" className="fruit-preview" />
                ) : (
                  <div className="upload-placeholder">
                    <span className="upload-icon">📷</span>
                    <strong>Your fresh scan starts here</strong>
                    <p>Take a photo or choose an image from your device.</p>
                  </div>
                )}
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {preview ? "Change photo" : "Scan or upload fruit"}
                </button>
              </div>

              <div className="field-group">
                <label htmlFor="produce">What are you scanning?</label>
                <div className="produce-options" id="produce">
                  {produceOptions.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      className={`produce-option ${
                        produceType === item.value ? "selected" : ""
                      }`}
                      onClick={() => {
                        setProduceType(item.value);
                        setResult(null);
                      }}
                      aria-pressed={produceType === item.value}
                    >
                      <span>{item.emoji}</span>
                      {item.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="environment-heading">
                <div>
                  <span className="eyebrow">02 / STORAGE CONDITIONS</span>
                  <h2>Environment</h2>
                </div>
                <button
                  type="button"
                  className="weather-button"
                  onClick={fetchWeather}
                  disabled={weatherLoading}
                >
                  {weatherLoading ? "Loading..." : "☀ Use local weather"}
                </button>
              </div>

              {weatherMessage && (
                <p className="weather-note" role="status">{weatherMessage}</p>
              )}

              {weather && (
                <p className="weather-detail">
                  Latest outdoor reading: {weather.temperature}°C,
                  {" "}{weather.humidity}% humidity.
                  Storage conditions may differ.
                </p>
              )}

              <div className="input-grid">
                <div className="field-group">
                  <label htmlFor="temperature">Temperature (°C)</label>
                  <input
                    id="temperature"
                    type="number"
                    min="-20"
                    max="60"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(e.target.value)}
                    required
                  />
                </div>

                <div className="field-group">
                  <label htmlFor="humidity">Humidity (%)</label>
                  <input
                    id="humidity"
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={humidity}
                    onChange={(e) => setHumidity(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="field-group">
                <label htmlFor="storage-environment">
                  Storage environment
                </label>
                <select
                  id="storage-environment"
                  value={storageEnvironment}
                  onChange={(e) => {
                    setStorageEnvironment(e.target.value);
                    setResult(null);
                  }}
                >
                  <option value="">Not specified</option>
                  <option value="room">Room / indoors</option>
                  <option value="shade">Outdoor shade</option>
                  <option value="sun">Direct sunlight</option>
                </select>
              </div>

              <div className="field-group">
                <label htmlFor="storage-days">Days already in storage</label>
                <input
                  id="storage-days"
                  type="number"
                  min="0"
                  step="0.5"
                  value={storageDays}
                  onChange={(e) => setStorageDays(e.target.value)}
                  required
                />
              </div>

              <p className="input-hint">
                Use the actual storage temperature and humidity when known.
                Local weather is only an outdoor reference.
              </p>

              <button className="analyze-button" type="submit" disabled={loading}>
                {loading ? "Analyzing your fruit..." : "Analyze freshness & shelf life"}
                {!loading && <span aria-hidden="true">→</span>}
              </button>
            </form>

            {error && <p className="error-message" role="alert">{error}</p>}
          </section>

          <aside className="results-column">
            <section className="panel results-panel" aria-live="polite">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">03 / AI INSIGHTS</span>
                  <h2>Your analysis</h2>
                </div>
                <span className="section-icon">✧</span>
              </div>

              {result ? (
                <div className="results-content">
                  <div className="result-produce">
                    <span className="result-emoji">{selectedProduce?.emoji}</span>
                    <div>
                      <span className="muted">Analyzed produce</span>
                      <h3>{result.produce_type}</h3>
                    </div>
                  </div>

                  <div className="status-card">
                    <span className="muted">Visual freshness</span>
                    <strong className="status-value">
                      {result.freshness_status === "fresh"
                        ? "Fresh"
                        : "Rotten"}
                    </strong>
                    <span className="muted">
                      Fresh-class score:{" "}
                      {(result.freshness_score * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="shelf-life-card">
                    <span className="muted">
                      {result.predicted_remaining_days != null
                        ? "Experimental ML estimate to spoilage stage 3"
                        : "Shelf-life ML estimate unavailable"}
                    </span>

                    <div className="days-value">
                      {result.predicted_remaining_days != null
                        ? result.predicted_remaining_days
                        : "—"}
                      {result.predicted_remaining_days != null && (
                        <span>days</span>
                      )}
                    </div>

                    <p>
                      {result.predicted_remaining_days != null
                        ? "Random Forest estimate based on fruit type, storage environment, temperature and time already stored. Not food-safety validated."
                        : result.produce_type === "orange"
                          ? "The shelf-life regression model has no orange training data. Visual freshness analysis remains available."
                          : "Select a storage environment to enable the experimental shelf-life model."}
                    </p>
                  </div>

                  {result.recommendations?.length > 0 && (
                    <div className="recommendations">
                      <h3>Storage recommendations</h3>
                      <ul>
                        {result.recommendations.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <p className="disclaimer">
                    {result.predicted_remaining_days != null
                      ? result.disclaimer
                      : "Shelf-life regression is unavailable for this selection. Visual freshness results are not a food-safety assessment."}
                  </p>
                </div>
              ) : (
                <div className="empty-results">
                  <div className="empty-icon">🌱</div>
                  <h3>Ready when you are</h3>
                  <p>
                    Upload a photo, enter storage conditions, and
                    run an analysis to see your results here.
                  </p>
                </div>
              )}
            </section>

            <section className="insight-panel">
              <span className="eyebrow">WHY FRESHSENSE?</span>
              <h3>Better storage starts with better information.</h3>
              <p>
                Combining visual AI with environmental inputs
                helps you explore freshness and storage conditions.
              </p>
            </section>
          </aside>
        </div>

        <footer className="footer">
          FreshSense AI · Academic research prototype ·
          Not intended for food safety decisions.
        </footer>
      </main>
    </div>
  );
}

export default App;
