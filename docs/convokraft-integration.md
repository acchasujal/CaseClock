# CaseClock ConvoKraft integration

Status: **code implemented; Catalyst Action configuration required**.

## Webhook

Configure the `voiceassistant` bot in Catalyst project `51441000000017001` to call:

```text
POST https://caseclock-backend-50043773125.development.catalystappsail.in/api/integrations/convokraft/action
```

Use ConvoKraft's documented webhook request and response formats. The endpoint returns the documented `execution` response with `status`, `message`, `card`, `data`, `broadcast`, `trigger`, and `followup` fields.

## Action

Create action `case_status_summary` and add these sample sentences:

- How many cases are pending?
- Give me the current case workload.
- What cases require immediate attention?
- How many cases are overdue?

The action computes counts from the CaseClock worklist and clock state. It does not use QuickML or an LLM for numeric values.

Optional actions implemented by the endpoint:

- `urgent_cases`
- `deadline_summary`
- `case_detail_summary` with `params.case_id` or `params.fir_number`

## Security and role context

In Catalyst Console, enable ConvoKraft webhook security and copy the generated DSA public key into AppSail as:

```text
CONVOKRAFT_PUBLIC_KEY=<public PEM key>
```

The endpoint verifies `X-CONVOKRAFT-SIGNATURE` in production and rejects requests when the key/signature is missing or invalid. The current demo role is read from the documented webhook `clientData.role` object and accepts only `IO`, `SHO`, or `SP`. Because ConvoKraft does not provide a CaseClock-verified identity in this integration, production identity/role trust requires a signed, authoritative role mapping before enabling sensitive use.

## Console steps

1. Open Catalyst project `51441000000017001` and bot `voiceassistant`.
2. Create the `case_status_summary` action.
3. Add the sample sentences above.
4. Choose Webhook as the action business-logic platform.
5. Set the webhook URL above and configure invocation after action execution.
6. Enable webhook security and copy the generated public key to AppSail as `CONVOKRAFT_PUBLIC_KEY`.
7. Train/deploy the bot.
8. Test `How many cases are pending?` and compare the response with the CaseClock worklist.

The endpoint is subject to ConvoKraft's documented webhook timeout and response-size limits.
