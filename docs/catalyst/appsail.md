# AppSail

## Capability

Validate Catalyst AppSail as the deployment target for:

- Minimal backend service
- Minimal frontend hosting
- Frontend to backend communication over HTTPS

This spike must not implement Case Clock application logic.

## Status

PENDING

No Catalyst project credentials, AppSail service URL, Slate/Web Client URL, or deployment logs are present in this repository.

## Evidence

Record the actual validation evidence here after running the spike.

### Backend Proof of Concept

Minimal endpoints to deploy:

```text
GET /health
GET /hello
POST /echo
```

Expected checks:

| Check | Result | Evidence |
|---|---|---|
| Deployment succeeds | PENDING | Add AppSail deployment log or screenshot |
| `/health` reachable | PENDING | Add HTTPS URL and response JSON |
| `/hello` returns JSON | PENDING | Add response body |
| `/echo` accepts POST JSON | PENDING | Add request and response body |
| Environment variable readable | PENDING | Add sanitized variable name and observed value class |
| Routing works | PENDING | Add endpoint results |
| Request handling works | PENDING | Add status codes |
| API latency measured | PENDING | Add p50/p95 or manual timing |

Suggested response examples:

```json
{ "status": "ok", "service": "caseclock-catalyst-spike" }
```

```json
{ "message": "hello from Catalyst AppSail" }
```

```json
{ "received": { "sample": true } }
```

### Frontend Proof of Concept

Expected checks:

| Check | Result | Evidence |
|---|---|---|
| Frontend deploys | PENDING | Add deployment log or screenshot |
| HTTPS URL loads | PENDING | Add URL |
| Static assets load | PENDING | Add screenshot or network tab evidence |
| Refresh works on routed page | PENDING | Add tested route |
| Frontend can call backend | PENDING | Add browser screenshot showing API response |
| Error handling renders | PENDING | Add screenshot or notes |

### Frontend to Backend

Expected checks:

| Check | Result | Evidence |
|---|---|---|
| Browser API call succeeds | PENDING | Add endpoint and response |
| CORS allows deployed frontend origin | PENDING | Add CORS header evidence |
| HTTPS to HTTPS works | PENDING | Add URL pair |
| Latency acceptable | PENDING | Add measured latency |
| Backend error is handled | PENDING | Add error-state screenshot |

## Limitations

- This repository does not contain Catalyst credentials or live deployment URLs.
- AppSail runtime, startup command, environment variable handling, cold starts, and routing behavior remain unverified until deployed on Catalyst.
- If Catalyst requires a change to API contracts, shared DTOs, graph schema, folder structure, or architecture, do not modify those frozen files in this spike. Document the limitation in `docs/catalyst/limitations.md`.

## Recommendation

Do not start production feature work that depends on AppSail until this spike has live deployment evidence.

Once verified, update this file with:

- Runtime
- Startup command
- Deployment steps
- Sanitized environment variable proof
- Endpoint screenshots or command output
- Latency observations
- Cold start observations
- Any Catalyst-specific constraints
