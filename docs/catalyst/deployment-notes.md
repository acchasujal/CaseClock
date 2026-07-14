# Catalyst Deployment Notes

## Purpose

This document records the deployment process and validation results obtained during the Catalyst technical spikes.

These notes are operational evidence for the Phase A Technical Validation and are **not** intended to serve as a production deployment runbook.

---

# Status

🟢 COMPLETE

Deployment validation completed successfully.

Validated:

- ✅ Catalyst AppSail deployment
- ✅ Catalyst Slate deployment
- ✅ Frontend ↔ Backend communication
- ✅ HTTPS communication
- ✅ Express backend hosting
- ✅ React + Vite frontend hosting

---

# Project Information

| Field | Value |
|------|-------|
| Catalyst Project | CaseClock |
| Project ID | 51441000000017001 |
| Region | India |
| Environment | Development |
| Operator | Ram Panjwani |
| Validation Date | 12 July 2026 |

---

# Backend Deployment (AppSail)

| Field | Value |
|------|-------|
| Runtime | Node.js 22 (Managed Runtime) |
| Hosting Service | Catalyst AppSail |
| Startup Command | `node index.js` |
| Build Directory | `.` |
| Deployment Method | Catalyst CLI |
| Deployment Command | `catalyst deploy appsail` |
| Deployment Status | ✅ Success |
| Backend URL | https://caseclock-backend-50043773125.development.catalystappsail.in |
| Environment Variable | `X_ZOHO_CATALYST_LISTEN_PORT` |
| Cold Start | Not measured |
| Warm Request Latency | Not measured |

---

# Frontend Deployment (Slate)

| Field | Value |
|------|-------|
| Framework | React + Vite |
| Hosting Service | Catalyst Slate |
| Deployment Method | Catalyst CLI |
| Build Command | `npm run build` |
| Development Command | `npm run dev -- --port $ZC_SLATE_PORT` |
| Output Directory | `dist` |
| Deployment Status | ✅ Success |
| HTTPS Verified | ✅ Yes |
| Frontend ↔ Backend | ✅ Working |

---

# Integration Validation

| Check | Result |
|------|--------|
| Frontend deployed | ✅ PASS |
| Backend deployed | ✅ PASS |
| HTTPS enabled | ✅ PASS |
| Frontend fetched `/health` | ✅ PASS |
| JSON parsed correctly | ✅ PASS |
| Backend status displayed | ✅ PASS |
| Browser ↔ Backend communication | ✅ PASS |

Observed frontend output:

```text
CaseClock Catalyst AppSail Spike

Backend Status

ok
```

---

# Deployment Observations

## AppSail

- Managed Runtime deployment completed successfully.
- Startup command `node index.js` worked without modification.
- Express application successfully bound to the Catalyst-provided listening port.
- Public HTTPS endpoint generated automatically.

---

## Slate

- Existing React + Vite application successfully linked using `catalyst slate:link`.
- Framework detection was automatic.
- Default build configuration was sufficient.
- Deployment completed without additional configuration.

---

## CORS

During browser testing, frontend requests initially failed because CORS headers were not configured.

Firefox reported:

```text
Cross-Origin Request Blocked

Access-Control-Allow-Origin missing.
```

Resolution:

```javascript
const cors = require("cors");

app.use(cors());
```

After redeploying the backend, frontend communication succeeded.

This was an application configuration issue rather than a Catalyst platform limitation.

---

# SmartBrowz

| Field | Value |
|------|-------|
| Capability Tested | HTML → PDF |
| Result | ✅ Successful |
| Formatting | Acceptable |
| Unicode | Verified |
| Tables | Verified |
| Images | Verified |
| Page Breaks | Verified |

---

# Zia

| Field | Value |
|------|-------|
| Speech Services Available | ❌ No |
| STT Tested | No |
| TTS Tested | No |
| Decision | Text interface remains primary demo path |

---

# Limitations

Not evaluated during this spike:

- Cold start behaviour
- Load testing
- Concurrent requests
- API latency benchmarking

No Catalyst deployment limitations requiring architectural changes were identified.

---

# Conclusion

The proposed deployment architecture has been successfully validated.

Recommended production architecture:

- **Frontend:** Catalyst Slate
- **Backend:** Catalyst AppSail
- **PDF Generation:** SmartBrowz
- **Voice:** Optional (pending Zia Speech availability)

No changes to the project's frozen architecture, contracts, or shared schemas are required based on the results of this validation.