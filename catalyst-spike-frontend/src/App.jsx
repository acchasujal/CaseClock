import { useEffect, useState } from "react";

const BACKEND =
  "https://caseclock-backend-50043773125.development.catalystappsail.in";

export default function App() {
  const [status, setStatus] = useState("Loading...");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${BACKEND}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>CaseClock Catalyst AppSail Spike</h1>

      <h2>Backend Status</h2>

      <p>{status}</p>

      {error && (
        <>
          <h3>Error</h3>
          <pre>{error}</pre>
        </>
      )}
    </div>
  );
}