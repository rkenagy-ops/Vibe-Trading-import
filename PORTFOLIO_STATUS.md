# Portfolio integration status — 2026-08-10

## Local connection framework V4 — 2026-08-11

- Portfolio settings now reference credential-free local `connection_id`
  values instead of embedding a static profile selection.
- Existing profile-based IBKR, Longbridge, and Binance settings migrate into
  owner-only `connections.json` metadata without moving or exposing secrets.
- User connectors are discovered from `~/.vibe-trading/connectors`; strict
  manifest validation rejects write capabilities and requires account and
  position reads.
- Local Python adapters share a three-operation read contract and are loaded
  only after the operator installs them outside the Git checkout.
- Plugin-declared credential values use the operating-system credential vault;
  connection and portfolio APIs expose only field-level configured state.
- The Web Connection Center creates account instances, stores plugin
  credentials, checks readiness, and keeps portfolio selection separate.
- `connector init`, `connector validate`, and `connector install` provide the
  intended Codex-assisted local onboarding workflow.

## Configurable portfolio V3 — 2026-08-11

- Portfolio sources are no longer fixed to three connector names. The dashboard
  discovers eligible read-only `TradingProfile` entries from the shared
  connector registry.
- The new Manage Accounts drawer can add, disable, rename, reorder, and remove
  sources, include/exclude account cash, and choose USD or CNY as the primary
  display currency.
- Credential-free settings are stored in owner-only
  `~/.vibe-trading/portfolio.json`; API keys and OAuth tokens remain in their
  existing connector stores.
- The settings API rejects non-read-only profiles and arbitrary connector URLs
  or commands. Refresh progress, account filtering, cards, colors, reconnect,
  and cache fallback are keyed by configured source id.
- Existing three-account installations migrate automatically when the legacy
  snapshot database exists. A new installation starts with no selected source.
- A generic field normalizer supports connector-standard account and position
  envelopes, while IBKR, Longbridge, and Binance retain their verified special
  valuation paths.
- Live migration validation completed with IBKR, Longbridge, and Binance: all
  three sources refreshed successfully (7, 3, and 5 positions respectively),
  and the resulting snapshot was complete.

## Current scope

- Local Web dashboard aggregates IBKR, Longbridge, and Binance Spot.
- Refresh is manual and snapshots accumulate from the first successful run.
- All portfolio connectors are selected through read-only profiles.
- The LLM-facing context removes credentials, account identifiers, order IDs,
  names, and local paths.
- A failed broker refresh now carries forward that broker's last successful
  account/position data, marks it cached, and preserves the original success
  timestamp. Partial refresh events are retained in SQLite but excluded from
  the asset-history chart.
- Longbridge position prices are read through the official SDK in the isolated
  worker. The previous public Eastmoney dependency is no longer the default.
- Ordinary portfolio refresh is non-interactive for IBKR. If OAuth really
  requires user consent, the page exposes a separate explicit reconnect action.

## Credential lifetime findings

- IBKR MCP access tokens observed locally last about 600 seconds. The cached
  refresh token is used on demand; IBKR does not publish its fixed lifetime.
- The currently configured Longbridge legacy Access Token expires after 90
  days by default. Longbridge supports issuing a longer token (for example,
  three years), but the legacy credential may permit trading at the provider,
  so migration to scoped OAuth is preferred over merely extending it.
- Binance read-only API keys do not use a short login session or refresh-token
  cycle. They remain usable until revoked, disabled, expired by provider policy,
  or rejected by a changed IP restriction. Rotation is security maintenance,
  not a login requirement.

## Permission audit

### IBKR

- Official MCP endpoint, without TWS or IB Gateway.
- OAuth token scope verified from the live cache: `mcp.read` only.
- Local MCP allow-list is limited to `get_account_summary` and
  `get_account_positions`.
- Generic order placement and cancellation both fail before contacting IBKR.

### Binance

- Binance's signed API restriction endpoint reports reading enabled.
- Spot/margin trading, withdrawals, internal transfers, futures, options, and
  portfolio-margin trading are all disabled on the API key.
- The application also selects `binance-live-sdk-readonly`; generic order
  placement and cancellation fail before contacting Binance.
- IP restriction is not enabled on the key. This does not grant write access,
  but IP allow-listing would further protect account-read privacy.

### Longbridge

- The application selects `longbridge-live-sdk-readonly`.
- Generic order placement and cancellation fail before contacting Longbridge.
- The connector has a hard live-account guard: its order functions accept only
  the declared paper environment, so live orders cannot be submitted through
  this code path.
- Longbridge does not expose a comparable API permission-inspection response,
  so the provider-side Access Token scope could not be independently proven as
  read-only. The local integration is nevertheless structurally read-only.

## Issues found and disposition

### 1. IBKR access-token renewal returned 404

- Symptom: an otherwise valid cached login stopped reading IBKR after the
  short-lived access token expired.
- Observed access-token lifetime: `599` seconds (about 10 minutes).
- This is only the lifetime of each short-lived access token, not the lifetime
  of the user's MCP authorization. The response also contains an opaque refresh
  token, and IBKR's OAuth metadata advertises the `refresh_token` grant. IBKR
  does not expose a refresh-token expiry field in the response, so no exact
  multi-day authorization lifetime should be claimed without a published IBKR
  policy.
- A refresh token is present and renewal should be automatic.
- Root cause: after a client restart, refresh could run before IBKR's official
  token endpoint was pinned, causing the OAuth library to use a bad discovered
  URL.
- Fix: pin IBKR OAuth metadata during client initialization, before refresh is
  attempted. Account summary and eight positions were read successfully after
  the fix.

### 2. Browser OAuth callback could close before consent returned

- Symptom: `localhost:8765/callback?...` showed connection refused.
- Cause: ordinary portfolio refresh uses a 30-second tool deadline. If a full
  interactive login is required, that request can end before the user returns
  from IBKR.
- Current recovery: use `vibe-trading connector authorize
  ibkr-live-official-mcp-readonly`, whose interactive deadline is five minutes.
- Follow-up: add a dedicated Web reconnect flow that runs independently from a
  portfolio refresh and exposes pending/success/error state.

### 3. Longbridge public quote source is intermittent

- Symptom: one or more Longbridge positions can be marked unpriced when the
  Eastmoney endpoint or local proxy disconnects.
- Impact: Longbridge account total still comes from the broker's net-assets
  value, but the holding-allocation chart groups the difference under
  `Cash/unpriced`.
- Resolved: Longbridge quotes are now fetched through the already isolated
  official SDK worker. A quote failure does not discard the broker-reported
  net asset total.

### 5. Partial refreshes looked like real asset losses

- Symptom: a transient broker failure produced historical points around only
  the remaining connected accounts, making the history chart look like a large
  loss.
- Resolved: failed brokers use last-known-good data with a visible cached badge;
  asset history reads complete snapshots only. Existing incomplete rows remain
  archived and are not deleted.

## Portfolio page V2

- Primary metrics: total USD/CNY, today's asset change, valuation coverage, and
  last complete update.
- Stable broker colors and percentage doughnut charts; broker cards filter the
  holdings table.
- Account cards show fresh/cached/error state and last successful timestamp.
- Holdings show portfolio weight, sensible price precision, and data freshness.
- Complete-only line history replaces the unlabeled snapshot bars.
- Connection cards explain renewal mode and whether read-only is proven at the
  provider or only enforced locally.
- Manual refresh exposes per-broker progress; IBKR reconnect is a separate
  explicit action.

### 4. Local Web server lifecycle

- The dashboard is served at `http://localhost:8899/portfolio` by a local
  process. It is unavailable if that process exits or the computer restarts.
- Follow-up: add a simple start/stop launcher (and optional login startup) after
  the integration behavior is stable.

## Verification completed

- IBKR account summary and positions: live read succeeded after renewal fix.
- Binance provider-side API restrictions: live read succeeded.
- Read-only place/cancel guards: verified for all three selected profiles
  without sending any order request.
- Portfolio backend tests, OAuth tests, and Portfolio page tests pass.
- Production frontend build succeeds and `/portfolio` serves HTML while
  `/api/portfolio` serves snapshot JSON.
- Live V2 refresh succeeded for all three accounts without opening IBKR login;
  all current IBKR, Longbridge, and Binance positions were priced.
