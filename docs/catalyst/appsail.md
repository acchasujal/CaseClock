# AppSail

## Capability

Validate Catalyst deployment services for the CaseClock application.

Validated deployment architecture:

- Backend hosted using **Catalyst AppSail**
- Frontend hosted using **Catalyst Slate (React + Vite)**
- Secure frontend ↔ backend communication over HTTPS

This spike validates the deployment platform only. No CaseClock business logic was implemented.

---

# Status

🟢 COMPLETE

Deployment validation completed successfully.

Validated:

- ✅ Backend deployment (AppSail)
- ✅ Frontend deployment (Slate)
- ✅ Frontend ↔ Backend communication
- ✅ HTTPS communication
- ✅ Routing
- ✅ JSON request handling
- ✅ Environment variable support
- ✅ CORS configuration

Remaining optional observations:

- API latency measurement
- Cold start behaviour

---

# Evidence

## Backend Proof of Concept

### Deployment Details

| Item | Value |
|------|-------|
| Runtime | Node.js 22 (Managed Runtime) |
| Hosting | Catalyst AppSail |
| Deployment Method | Catalyst CLI |
| Startup Command | `node index.js` |
| Deployment Status | ✅ Success |
| Backend URL | https://caseclock-backend-50043773125.development.catalystappsail.in |

Implemented endpoints

```text
GET /health
GET /hello
POST /echo
```

---

## Backend Validation Results

| Check | Result | Evidence |
|---|---|---|
| Deployment succeeds | ✅ PASS | Successfully deployed using Catalyst CLI |
| `/health` reachable | ✅ PASS | Returns expected JSON |
| `/hello` returns JSON | ✅ PASS | Returns expected JSON |
| `/echo` accepts POST JSON | ✅ PASS | Successfully echoed request body |
| Environment variable readable | ✅ PASS | Bound to `X_ZOHO_CATALYST_LISTEN_PORT` |
| Routing works | ✅ PASS | Multiple endpoints reachable |
| Request handling works | ✅ PASS | HTTP 200 responses |
| API latency measured | ⏳ Pending | Not measured |

---

## Sample Responses

### GET /health

```json
{
  "status": "ok",
  "service": "CaseClock AppSail Spike"
}
```

### GET /hello

```json
{
  "message": "Hello Catalyst"
}
```

### POST /echo

Request

```json
{
  "name": "Ram",
  "test": true
}
```

Response

```json
{
  "name": "Ram",
  "test": true
}
```

---

# Frontend Proof of Concept

### Deployment Details

| Item | Value |
|------|-------|
| Framework | React + Vite |
| Hosting | Catalyst Slate |
| Deployment Method | Catalyst CLI |
| Deployment Status | ✅ Success |
| Deployment | Live |
| Build | Production |

---

## Frontend Validation Results

| Check | Result | Evidence |
|---|---|---|
| React + Vite detected | ✅ PASS | Auto-detected by Slate |
| Frontend deployment | ✅ PASS | Successfully deployed |
| HTTPS page loads | ✅ PASS | Live application accessible |
| Static assets load | ✅ PASS | Verified |
| Routing works | ✅ PASS | Root page rendered |
| Frontend communicates with backend | ✅ PASS | Backend status displayed as `ok` |
| Error handling | ✅ PASS | CORS issue identified and resolved |

---

# Frontend → Backend Validation

| Check | Result | Evidence |
|---|---|---|
| Browser API call succeeds | ✅ PASS | `/health` successfully fetched |
| HTTPS → HTTPS communication | ✅ PASS | Verified |
| JSON parsed correctly | ✅ PASS | React displayed backend status |
| CORS configured correctly | ✅ PASS | Express `cors` middleware enabled |
| Backend reachable from deployed frontend | ✅ PASS | Backend status displayed successfully |
| Latency measured | ⏳ Pending | Not measured |

---

# Observations

## Deployment

Backend deployment using Catalyst AppSail completed successfully.

Frontend deployment using Catalyst Slate automatically detected the existing React + Vite project and built it successfully.

Catalyst deployment required no modifications to the React or Express application structure.

The backend successfully listened on the Catalyst-provided port using:

```javascript
process.env.X_ZOHO_CATALYST_LISTEN_PORT
```

---

## CORS

During frontend integration, browser requests initially failed because the backend did not expose CORS headers.

Firefox reported:

```text
Cross-Origin Request Blocked:
Access-Control-Allow-Origin missing.
```

Resolution:

```javascript
const cors = require("cors");

app.use(cors());
```

After redeploying the backend, communication succeeded.

This was an application configuration issue rather than a Catalyst limitation.

---

## Frontend Integration

The deployed React application successfully communicated with the deployed AppSail backend.

Observed output:

```text
CaseClock Catalyst AppSail Spike

Backend Status

ok
```

Validated:

- React + Vite hosting
- Catalyst Slate deployment
- HTTPS networking
- Backend accessibility
- JSON parsing
- Cross-origin communication

---

# Known Limitations

Not evaluated during this spike:

- Cold start behaviour
- API latency
- Load testing
- Concurrent request performance

No Catalyst-specific deployment blockers were encountered.

---

# Decision

## Result

✅ Catalyst deployment architecture is suitable for CaseClock.

Validated capabilities:

- Catalyst AppSail backend hosting
- Catalyst Slate frontend hosting
- HTTPS communication
- Environment variables
- Routing
- Browser ↔ Backend communication
- Express applications
- React + Vite applications

No modifications were required to:

- Graph schema
- DTOs
- API contracts
- Folder structure
- Overall architecture

---

# Recommendation

Recommended deployment architecture:

- **Backend:** Catalyst AppSail
- **Frontend:** Catalyst Slate
- **PDF Export:** SmartBrowz

Catalyst successfully supports the proposed architecture for CaseClock.

The only issue encountered during validation was missing CORS headers in the Express backend. This was resolved by enabling Express CORS middleware and does not represent a Catalyst platform limitation.

No architectural changes are required based on this spike.