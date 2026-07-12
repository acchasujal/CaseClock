# AppSail

## Capability

Validate Catalyst AppSail as the deployment target for:

- Minimal backend service
- Minimal frontend hosting
- Frontend to backend communication over HTTPS

This spike does **not** implement CaseClock business logic. It validates the deployment platform only.

---

# Status

🟢 COMPLETE

Backend and frontend deployment validation completed successfully.

Validated:

- ✅ Backend deployment
- ✅ Frontend deployment
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
| Deployment Method | Catalyst CLI |
| Startup Command | `node index.js` |
| Build Directory | `.` |
| Deployment Status | ✅ Success |
| Backend AppSail URL | https://caseclock-backend-50043773125.development.catalystappsail.in |

Implemented endpoints:

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
| `/echo` accepts POST JSON | ✅ PASS | Successfully echoed request body using `Invoke-RestMethod` |
| Environment variable readable | ✅ PASS | Application successfully bound to `X_ZOHO_CATALYST_LISTEN_PORT` |
| Routing works | ✅ PASS | Multiple routes reachable |
| Request handling works | ✅ PASS | HTTP 200 responses |
| API latency measured | ⏳ Pending | Not yet measured |

---

## Observed Responses

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

| Check | Result | Evidence |
|---|---|---|
| Frontend application created | ✅ PASS | Minimal React/Vite application |
| Frontend loads successfully | ✅ PASS | Application renders correctly |
| Static assets load | ✅ PASS | Verified |
| Routing works | ✅ PASS | Root route loads correctly |
| Frontend can call backend | ✅ PASS | Backend status displayed as `ok` |
| Error handling tested | ✅ PASS | Initial CORS issue reproduced and resolved |

---

# Frontend → Backend Validation

| Check | Result | Evidence |
|---|---|---|
| Browser API call succeeds | ✅ PASS | `/health` returned expected JSON |
| CORS configured correctly | ✅ PASS | Express `cors` middleware enabled |
| HTTPS to HTTPS communication | ✅ PASS | Successfully verified |
| JSON response parsed | ✅ PASS | React displayed backend status |
| Backend errors observable | ✅ PASS | Initial CORS failure documented |
| Latency acceptable | ⏳ Pending | Not measured |

---

# Observations

## Deployment

- Catalyst CLI deployment completed successfully.
- Managed Runtime (Node.js 22) works without additional configuration.
- Startup command `node index.js` worked correctly.
- Public HTTPS endpoint was generated automatically.
- Backend routing functioned as expected.
- Application successfully bound to the Catalyst-provided listening port using:

```javascript
process.env.X_ZOHO_CATALYST_LISTEN_PORT
```

---

## CORS

During frontend integration testing, browser requests initially failed.

Firefox reported:

```text
Cross-Origin Request Blocked:
The Same Origin Policy disallows reading the remote resource.
Reason:
Access-Control-Allow-Origin missing.
```

The backend itself remained healthy and returned HTTP 200 responses.

Resolution:

```javascript
const cors = require("cors");

app.use(cors());
```

After redeploying the backend, frontend-to-backend communication succeeded.

This was an application configuration issue rather than an AppSail platform limitation.

---

## Frontend Integration

The frontend successfully retrieved backend data using HTTPS.

Displayed result:

```text
CaseClock Catalyst AppSail Spike

Backend Status

ok
```

This validates:

- React frontend deployment
- Browser networking
- HTTPS communication
- JSON parsing
- Backend accessibility

---

# Known Limitations

Remaining optional observations:

- Cold start behaviour after idle timeout
- API latency measurements

No Catalyst-specific deployment blockers were identified during this spike.

---

# Decision

## Result

✅ AppSail is suitable for hosting the CaseClock application.

Validated capabilities:

- Backend deployment
- Frontend deployment
- HTTPS hosting
- Routing
- Environment variables
- Browser ↔ Backend communication
- JSON request handling
- Express applications
- React frontend hosting

No changes to:

- Graph schema
- DTOs
- Folder structure
- API contracts
- Overall architecture

were required.

---

# Recommendation

Proceed with AppSail as the deployment platform for both frontend and backend services.

The only issue encountered during validation was missing CORS headers in the Express backend. This was resolved by enabling Express CORS middleware and does not represent a Catalyst platform limitation.

No architectural changes are required based on the results of this spike.