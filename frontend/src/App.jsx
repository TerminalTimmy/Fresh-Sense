
import { useState } from "react";
import "./App.css";

function App() {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [produceType, setProduceType] = useState("apple");
  const [temperature, setTemperature] = useState(20);
  const [humidity, setHumidity] = useState(60);
  const [storageDays, setStorageDays] = useState(2);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleImageChange(event) {
    const file = event.target.files[0];
    if (!file) return;

    setImage(file);
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError("");
  }

  async function handlePredict(event) {
    event.preventDefault();

    if (!image) {
      setError("Please upload a fruit image.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("image", image);
    formData.append("temperature", temperature);
    formData.append("humidity", humidity);
    formData.append("storage_days", storageDays);
    formData.append("produce_type", produceType);

    try {
      const response = await fetch(
        import.meta.env.VITE_API_URL + "/predict",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Prediction request failed.");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Fruit Shelf Life Prediction</h1>
        <p>
          Multimodal Machine Learning for Freshness Analysis
          and Storage Optimization
        </p>
      </header>

      <main className="container">
        <section className="card">
          <h2>Analyze Your Fruit</h2>

          <form onSubmit={handlePredict}>
            <label>Upload Fruit Image</label>
            <input
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              required
            />

            {preview && (
              <img
                src={preview}
                alt="Fruit preview"
                className="preview"
              />
            )}

            <label>Fruit Type</label>
            <select
              value={produceType}
              onChange={(e) => setProduceType(e.target.value)}
            >
              <option value="apple">Apple</option>
              <option value="banana">Banana</option>
              <option value="orange">Orange</option>
            </select>

            <label>Temperature (°C)</label>
            <input
              type="number"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
              required
            />

            <label>Humidity (%)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={humidity}
              onChange={(e) => setHumidity(e.target.value)}
              required
            />

            <label>Storage Duration (Days)</label>
            <input
              type="number"
              min="0"
              value={storageDays}
              onChange={(e) => setStorageDays(e.target.value)}
              required
            />

            <button type="submit" disabled={loading}>
              {loading ? "Analyzing..." : "Analyze Freshness"}
            </button>
          </form>

          {error && <p className="error">{error}</p>}
        </section>

        {result && (
          <section className="card result">
            <h2>Prediction Results</h2>

            <p>
              <strong>Fruit:</strong> {result.produce_type}
            </p>

            <p>
              <strong>Freshness:</strong>{" "}
              {result.freshness_status}
            </p>

            <p>
              <strong>Fresh-class score:</strong>{" "}
              {(result.freshness_score * 100).toFixed(2)}%
            </p>

            <p>
              <strong>Illustrative Remaining Days:</strong>{" "}
              {result.illustrative_remaining_days ?? "N/A"}
            </p>

            <p className="disclaimer">
              {result.disclaimer}
            </p>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
