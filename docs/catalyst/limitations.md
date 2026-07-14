# Catalyst Limitations

## Purpose

This document records **verified Catalyst platform limitations** discovered during the CaseClock technical validation.

Only confirmed platform observations are recorded here. Application bugs or implementation mistakes are not considered Catalyst limitations.

---

# Status

🟢 COMPLETE

No critical Catalyst platform limitations were identified during Phase A Technical Validation.

The planned deployment architecture remains valid.

---

# Verified Observations

| Area | Observation | Evidence | Impact | Response |
|------|-------------|----------|--------|----------|
| AppSail | Startup command must be explicitly configured during deployment. | Successful deployment required `node index.js`. | Low | Document startup command. |
| AppSail | Applications must listen on `X_ZOHO_CATALYST_LISTEN_PORT`. | Express application successfully bound to the provided port. | Low | Use the environment variable instead of hardcoding ports. |
| Browser Integration | Browser requests require CORS headers. | Initial frontend requests failed until Express CORS middleware was enabled. | Low | Configure CORS in the application. Not a Catalyst limitation. |
| Slate | Existing React + Vite applications were automatically detected and deployed successfully. | Successful deployment using `catalyst slate:link`. | None | Use Slate for frontend hosting. |
| SmartBrowz | HTML → PDF generation worked successfully for tested documents. | Generated PDF rendered correctly. | None | Suitable for report generation. |
| Zia Speech | Speech services were unavailable in the current Catalyst project. | Service unavailable during validation. | Medium | Use text interaction for the demo. |

---

# Non-Issues

The following were validated successfully and are **not** considered platform limitations:

- ✅ Backend deployment
- ✅ Frontend deployment
- ✅ HTTPS hosting
- ✅ React + Vite support
- ✅ Express applications
- ✅ Environment variables
- ✅ Browser ↔ Backend communication
- ✅ Routing
- ✅ JSON APIs

---

# Architecture Impact

No Catalyst limitation requires changes to:

- Graph schema
- Shared DTOs
- API contracts
- CLOCK_RULES
- Folder structure
- Overall architecture

The existing CaseClock architecture remains valid.

---

# Remaining Unknowns

The following were outside the scope of this spike:

- Cold start behaviour
- API latency benchmarking
- Concurrent request performance
- Load testing
- Auto-scaling behaviour
- Production traffic limits

These should be evaluated during integration and performance testing.

---

# Recommendation

Proceed with the planned deployment architecture:

- **Frontend:** Catalyst Slate
- **Backend:** Catalyst AppSail
- **PDF Generation:** SmartBrowz

Use text interaction as the primary demo path until Zia Speech services become available.

No Catalyst platform blockers were identified during this validation.