# Catalyst Deployment Notes

## Capability

Record the Catalyst deployment process used during the validation spikes.

This document is operational evidence for the spike branch. It is not a production deployment runbook.

## Status

PENDING

No live Catalyst deployment has been performed from this workspace.

## Evidence

Fill this section after running the AppSail, frontend, SmartBrowz, and Zia validations.

### Project

| Field | Value |
|---|---|
| Catalyst project name | PENDING |
| Region | PENDING |
| Environment | PENDING |
| Operator | PENDING |
| Validation date | PENDING |

### Backend AppSail

| Field | Value |
|---|---|
| Runtime | PENDING |
| Startup command | PENDING |
| Service URL | PENDING |
| Environment variables configured | PENDING |
| Deployment command or console steps | PENDING |
| Deployment duration | PENDING |
| Cold start observation | PENDING |
| Warm request latency | PENDING |

### Frontend Hosting

| Field | Value |
|---|---|
| Hosting product used | PENDING |
| Build command | PENDING |
| Output directory | PENDING |
| Public URL | PENDING |
| Refresh route tested | PENDING |
| HTTPS verified | PENDING |

### SmartBrowz

| Field | Value |
|---|---|
| API or SDK used | PENDING |
| Test input | PENDING |
| Output PDF path | PENDING |
| Generation time | PENDING |
| Formatting result | PENDING |

### Zia

| Field | Value |
|---|---|
| STT API or SDK used | PENDING |
| TTS API or SDK used | PENDING |
| English STT latency | PENDING |
| Kannada STT latency | PENDING |
| English TTS latency | PENDING |
| Kannada TTS latency | PENDING |

## Limitations

- Catalyst console operations and credentials are external to this repository.
- Secrets must not be committed. Only record sanitized environment variable names and non-sensitive observations.
- Any Catalyst limitation that conflicts with frozen architecture must be documented in `docs/catalyst/limitations.md` before any architecture change is proposed.

## Recommendation

Use this file as the single place to record repeatable deployment steps and measured timings from the spike.
