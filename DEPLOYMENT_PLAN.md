# OS-DBX Remote Deployment Plan

**Status:** Implementation in progress; nothing has been deployed.  
**Last updated:** 2026-11-02  
**Cost target:** $0 recurring hosting cost for an initial prototype.  
**Primary requirement:** Inspect an explicitly authorized user's or inspector's remote system through a hosted web app and a separately installed collector. The workflow must not depend on the operator's localhost.

## Goal and operating model

OS-DBX is a web-based forensic observability tool. The web app is hosted centrally. A user who wants their own system observed, or an inspector who has been authorized by that system's owner, installs/runs the OS-DBX collector on the target machine. The collector sends the configured telemetry to the public OS-DBX HTTPS endpoint. The inspector signs in to the web app to review only the systems and records they are allowed to access.

The collector must be visible, scoped, authorized, revocable, and removable. It must not be installed on another person's system without that person's informed authorization. Collection paths, event types, retention, inspector identity, and start/stop times should be clear to the system owner.

```text
Target system (owner-authorized collector)
          │ outbound HTTPS; dedicated per-install/device credential
          ▼
Public HTTPS endpoint ── reverse proxy ── OS-DBX frontend/API ── MySQL
          ▲                                      │
          └──────── inspector's browser ─────────┘
```

The website alone cannot inspect another computer's local processes, files, or sockets. Host-level data requires a collector running on that host with the necessary OS permissions. A remote agent feed does not automatically prove a host-process-to-database connection; the relevant endpoints and database must be observable from a component with access to both sides.

## Proposed zero-recurring-cost prototype

### Candidate topology

Use one **Oracle Cloud Infrastructure Always Free Ampere A1 VM** for Docker Compose: frontend, backend, and MySQL on the same private Docker network. Put a TLS reverse proxy such as Caddy in front of the frontend. Publish only HTTPS (and HTTP for redirect/certificate validation); keep MySQL private and do not expose the backend port directly. The collector and browser use the same public HTTPS hostname; the frontend proxy routes `/api/` to FastAPI.

This uses the existing Compose architecture and avoids relying on a separate free hosted MySQL service. Oracle currently documents Always Free A1 usage equivalent to 2 OCPUs and 12 GB RAM, subject to home-region capacity; it can return an out-of-capacity error. OCI also documents that idle Always Free compute can be reclaimed. Check current limits and eligibility before creating resources: [OCI Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [OCI Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm).

Use a free DNS hostname only if its terms and operational limits fit; a custom domain is not assumed to be free. TLS certificates can be free, but a stable hostname and working public DNS are still required. Do not put secrets or investigative data in a public source repository.

### Why this is the first candidate

- It can run the whole app, including the MySQL version the backend currently expects, on one remote host.
- It gives the remote agent a stable HTTPS destination without a localhost dependency.
- It avoids Render Free's documented 15-minute idle spin-down, roughly one-minute wake-up, ephemeral local filesystem, and Free Postgres expiry after 30 days: [Render free service limits](https://render.com/docs/free).
- A static-only service such as Cloudflare Pages can host the frontend but still needs a separate API and durable database. Its static asset requests are free, while Functions have separate limits: [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/), [Cloudflare Pages pricing](https://developers.cloudflare.com/pages/functions/pricing/).
- Vercel Hobby is described as for personal, non-commercial use, so it is not the default recommendation for a tool that may be used by inspectors or organizations: [Vercel Hobby plan](https://vercel.com/docs/plans/hobby).

### Free-tier limitations

This is a prototype choice, not an availability or evidence-preservation guarantee. Free compute may be unavailable in the chosen region or reclaimed. A VM can fail, be suspended, or be misconfigured; a single VM is a single point of failure. The team must configure and test independent backups and restore procedures. A cloud VM, ordinary MySQL volume, or app audit table does not create tamper-evident chain of custody or immutable evidence. Do not use this free setup as the sole record in a real legal, regulatory, or high-stakes investigation.

## Production-readiness gate

**Production deployment is blocked until every scenario below has an implemented detection mechanism, documented expected behavior, recovery procedure, and recorded successful test.** A planned test is not a passed test. The current project has not completed these failure-injection tests, so all rows start as **NOT VERIFIED**. Free-tier deployment may be used only as a controlled prototype with consenting test devices and no reliance on it as the sole evidence source.

| # | Failure scenario | Detection and required behavior | Recovery procedure | Required test and current result |
|---:|---|---|---|---|
| 1 | Target loses Internet | Agent detects failed connection; dashboard marks device degraded/offline after a defined heartbeat timeout. Agent uses an encrypted, bounded, durable local queue and exposes queue health. | Retry with capped exponential backoff and jitter; resume upload on connectivity; deduplicate acknowledged events. Define queue-full policy and show any loss. | Disconnect network, generate events, reconnect, verify status transitions, complete ordered upload and no duplicates. **NOT VERIFIED** |
| 2 | Cloud VM/API unavailable | Health monitoring and heartbeat show service/device availability separately; collector treats timeouts/5xx as transient. | Controlled retry/backoff; restore from independent encrypted backups using the runbook; verify integrity before reopening service. | Stop VM/API, observe collector behavior, restore to a clean host from backup and verify records/configuration. **NOT VERIFIED** |
| 3 | Collector crashes, stops, or is uninstalled | Server-side heartbeat lease marks device unhealthy/offline; dashboard must never infer healthy solely from last registration. | Restart only according to owner/admin policy; reinstall/re-enroll after uninstall; preserve gap/last-seen status. | Kill, stop, and uninstall agent separately; verify timeout and re-enrollment behavior. **NOT VERIFIED** |
| 4 | Firewall, DNS, or TLS failure | Agent distinguishes DNS, connection, firewall, and certificate validation errors in safe status/logs; dashboard shows last successful contact and reason when reported. | Never bypass certificate validation; retry safely after correction; recover automatically after DNS/network/certificate repair. | Inject DNS failure, blocked port, expired/untrusted certificate; restore each and verify recovery. **NOT VERIFIED** |
| 5 | Database outage or disk full | Readiness/health checks, storage threshold alerts, structured API errors; no success response for unpersisted records. | Restore DB/storage capacity; retry idempotently; follow DB recovery and backup runbook. | Stop MySQL and simulate low disk/full disk; verify safe API behavior, alerts, no silent data loss, recovery. **NOT VERIFIED** |
| 6 | Inspector accesses another owner's device/data | Server-side authentication, RBAC, tenant isolation, device ownership and investigation-level authorization on every read/write/export, including SQL console, global metrics, bridge, audit and admin routes; return 401/403. | Revoke access, preserve access audit trail, investigate attempted access, correct authorization defect before reopening. | Use two tenants and cross-access attempts against every API route/export and privileged path. **NOT VERIFIED**; many pre-existing reads/writes are still global. |
| 7 | Device credential stolen, expired, or revoked | Per-device credential status and expiry; alert/audit credential failures and revocations. | Revoke immediately, reject subsequent ingestion, rotate credential and re-enroll device after owner verification. | Steal/use a test credential, revoke/expire/rotate it, verify old credential cannot ingest or read. **NOT VERIFIED**; credential checks added on the OS event endpoints but end-to-end tests and collector provisioning are pending. |
| 8 | Duplicate, delayed, or out-of-order events | Validate unique event ID and device ID; store device event time and server receipt time; expose sequence/gap information. | Idempotent insert/upsert; preserve original device time and receipt time; reconstruct timeline without rewriting source timestamps. | Retry the same event, delay/reorder a batch, verify one stored event and reconstructable timeline. **NOT VERIFIED** |
| 9 | Target clock incorrect | Record device timestamp, server receipt timestamp, timezone/offset where available, and clock-skew estimate. | Keep both clocks; flag skew and avoid presenting device time as trusted server time; use OS time synchronization where available. | Skew target clock forward/backward and verify warning and stable receipt ordering. **NOT VERIFIED** |
| 10 | Collector/target compromised | Minimize privileges and watched paths; validate/sanitize all input; monitor abnormal ingest; support device quarantine and credential revocation. | Disable device, revoke credentials, preserve relevant logs, investigate host, re-enroll only after remediation. | Submit malformed/oversized/spoofed events and simulate credential compromise; verify rejection/quarantine. **NOT VERIFIED** |
| 11 | Sensitive data collected unintentionally | Enforced collection allowlist, redaction/minimization, visible scope and collection status, retention/deletion controls. | Stop/restrict collector, delete affected records according to policy, record deletion action without copying sensitive data into audit logs. | Place test secrets in excluded paths/fields and verify neither collection nor display; exercise retention/deletion. **NOT VERIFIED** |
| 12 | Cloud/server compromise | MySQL private; only required HTTPS ingress public; protected secrets, patched OS/images, restricted admin access, rate limits, centralized audit logs and alerts. | Incident plan: isolate host, revoke/rotate credentials, preserve logs, rebuild from trusted images/backups, verify before restoring service. | Review external exposure and permissions; exercise credential rotation and host rebuild. **NOT VERIFIED** |
| 13 | Backup corrupt or restore fails | Backup job reports success only after integrity checks; alert on missed/failed runs; backups encrypted and stored outside the production VM, with independent credentials and a separately controlled archive copy. | Select last verified backup, restore to clean environment, validate data/schema, document recovery and gaps. | Corrupt a test backup and simulate failed restore; prove alerting and successful recovery from a copy not accessible with production VM credentials. **NOT VERIFIED** |
| 14 | High event volume/storage growth | Ingestion quotas, queue/database/storage metrics, warning and critical thresholds, retention and controlled archival policy. | Throttle/reject excess safely with visible status; archive/delete under approved retention; expand capacity only with cost approval. | Load-test burst and sustained growth, trigger thresholds, verify backpressure and no silent disk exhaustion. **NOT VERIFIED** |
| 15 | Bad deployment/version/migration | Deployment health checks, versioned migration status, release logs, backup checkpoint and alert on failed health/readiness. | Stop rollout; restore previous application image; roll back schema only if safe, otherwise restore verified backup and follow migration-specific recovery. | Deploy intentionally broken app and migration to staging; exercise rollback and data integrity checks. **NOT VERIFIED** |
| 16 | Investigation/evidence integrity | Record authenticated actor, device/investigation, timestamp, action and object for viewing/export/modification/deletion; protect provenance/integrity metadata and access logs. | Preserve audit records independently; investigate tampering; label any unverifiable data and do not claim legal chain of custody. | Verify audit coverage and tamper detection; alter/delete test records and confirm detection/recovery. **NOT VERIFIED**; no legally defensible chain-of-custody claim. |

## How we will fix this

Do this in dependency order. Keep the deployment private and limited to consenting test devices until the first two waves are complete. Do not try to “pass the checklist” by marking scenarios tested before their controls exist.

| Wave | Work | Scenarios covered | Exit condition |
|---|---|---|---|
| 0. Contain and define | No public deployment or third-party devices; rotate any real leaked credentials; set the supported OS, data scope, owner/inspector roles, and retention rules. Replace broad default watch paths with explicit, owner-approved scope before agent pilots. | 10, 11, 12, 16 | Written scope and consent model; no secrets in repo; pilot only on authorized test devices. |
| 1. Identity and isolation | Add tenants, owner/device ownership, invitations and grants, per-device credentials with revoke/rotate/expiry, and authorization on every route/query/export. Add negative-access checks for two tenants. | 6, 7, 10, 12, 16 | A user in tenant A cannot list, read, change, ingest for, or export tenant B's data; revoked device credentials are rejected. |
| 2. Reliable collector protocol | Add signed-in/registered device identity, heartbeat lease, online/degraded/offline states, stable event UUIDs with database uniqueness, server receipt timestamps, acknowledgement protocol, safe durable bounded local queue, exponential backoff/jitter, clock-skew signals, and clear dropped-event reporting. | 1, 2, 3, 4, 7, 8, 9 | Network/service/agent/clock failure tests pass; retries do not duplicate events; owner can see device health and revoke it. |
| 3. Data protection and limits | Enforce collection allowlists and redaction; define retention/deletion and archival; implement shared rate limits, streamed request-size limits, ingestion quotas/backpressure, disk/database monitoring and alerts. | 5, 10, 11, 14 | Sensitive test data is excluded/redacted; abuse and load tests trigger safe, visible limits without silent loss or disk exhaustion. |
| 4. Operations and recovery | Restrict public ingress to TLS proxy, keep backend/MySQL private, protect secrets, patch host/images, create independent encrypted backups, alert on failed/missed backups and storage thresholds, document restore and application/schema rollback. | 2, 4, 5, 12, 13, 14, 15 | Successful restore to a clean host and rollback from a bad app/schema release are recorded; recovered data integrity is checked before service returns. |
| 5. Investigation integrity | Audit investigator identity and access/export/change/delete actions; record event/device provenance and clock context; add integrity manifests/hash verification and preservation procedures if required by the use case. | 8, 9, 11, 16 | Audit coverage and integrity checks pass; reports clearly label gaps and do not claim legal chain of custody without a validated process. |
| 6. Release gate | Run the full 16-scenario failure-injection suite in staging, plus backend tests, frontend build, dependency checks, and end-to-end authorized-device workflow. Record owner, date, version, evidence, outcome, and remediation for every run. | 1–16 | Every row has an implemented control, documented recovery, passing result, and linked test evidence; otherwise remain prototype-only. |

### Source-based baseline (not a complete audit)

This focused check supports prioritization; it is not a verification of every path or an implementation test:

- **Present in some form:** admin/member authentication, login/signup throttling stored in process memory, an event ID field, workspace/device identity tables, device credential issuance and credential checks on the OS event ingestion routes.
- **Not end-to-end yet:** only OS event rows have a database uniqueness key for source event IDs. Deduplication has not been exercised under retries/races, receipt time is not consistently returned from persisted rows, and legacy feeds bypass this ingestion path.
- **Collector delivery gap:** the queue lives only in memory, caps by dropping old entries, and retries on a fixed delay. It is lost if the agent exits. There is no server heartbeat/device-health lease and no per-device credential registry/revocation flow.
- **Access gap:** operational data is shared in the workspace; route-level authentication/admin checks do not provide owner-to-inspector or tenant isolation.
- **Ingress/operations gap:** request-body middleware checks `Content-Length`, which does not cover chunked bodies. Login throttling is in-process, and the Compose MySQL volume has no independent backup/restore automation in the repo.
- **Scope/evidence gap:** there is no complete owner-approved collection-scope, redaction, retention/deletion, or tamper-evident evidence process. Broad agent watch-path defaults must be narrowed before a real user pilot.

### Cross-cutting blockers

- **Tenant isolation:** Current project behavior and README state that operational records are shared in one workspace. Do not expose it to multiple unrelated owners or inspectors until every record and API query is scoped to a tenant/device and grant.
- **Owner approval and revocation:** Add an enrollment/invitation flow. A device owner approves the inspector, scope, and duration; access and device credentials are revocable.
- **Per-device identity:** Device enrollment now issues unique, expiring, revocable credentials; OS event ingestion validates the credential and binds writes to its device/workspace. Collector provisioning and complete ingestion/read-path coverage remain incomplete.
- **Durable delivery and idempotency:** The current agent retry queue is in memory, and retries are not yet proven idempotent end-to-end. Implement a protected bounded disk queue, acknowledgements, stable event IDs, deduplication, and explicit queue-full handling before relying on offline buffering.
- **Data lifecycle:** Define collection scope, sensitive-field redaction, retention/deletion, archive, owner visibility, and deletion audit rules.
- **Evidence integrity:** Add provenance, dual timestamps, tamper-evident storage, signed checkpoints in an independently controlled archive, export hashes, and access history before any pilot. Current code does not establish legal chain of custody.
- **Operations:** Add multi-instance-capable rate limiting, ingress body-size enforcement (including streamed bodies), monitoring/alerts, independent encrypted backups, storage thresholds, and tested recovery/rollback runbooks.

NIST SP 800-61 Rev. 3 (finalized April 2025) frames incident response as preparation, detection, response, recovery, and continuous improvement. It calls for verifying restoration assets and restored systems before returning them to operation. This plan uses those principles as a deployment gate; it does not imply NIST certification. See [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) and the [NIST incident response project overview](https://csrc.nist.gov/projects/incident-response).

Until the approved design is implemented and the release gate passes, limit any deployment to a single trusted operator and explicitly consenting test devices. Do not treat collected data as complete or independently verified forensic evidence.

## Validated design decisions (2026-11-02)

The owner/inspector model, isolation approach, pilot envelope, and implementation order below were confirmed during planning. These are accepted design requirements; they are **not implemented or tested yet**.

### Product and access model

- Use one shared MySQL service with strict workspace/tenant scoping. Existing unowned records go to an admin-only legacy workspace during migration; never guess their owner.
- An owner can inspect their own devices and invite/revoke named inspectors for selected devices/investigations. Inspectors are read-only by default; export requires a separate explicit owner grant and is audited.
- Pilot accounts are invite-only. The named project operator controls the cloud account, secrets, backup keys, and recovery process. The platform administrator does not automatically receive tenant investigation access; break-glass access is time-limited, justified, and audited.
- Device enrollment is owner-approved and scoped. Each device has a unique revocable credential; request-supplied tenant/device IDs are not trusted. Credentials grant ingest only for their registered device.

### Collector, data, and evidence

- Initial collector targets: Windows, Linux, and macOS. Implement OS-specific protected-key backends (Windows DPAPI/Credential Manager, macOS Keychain, Linux Secret Service for desktop or systemd credentials for a managed service). Validate the chosen service mode during install. If no supported protected store is available, fail closed for durable offline mode; never fall back to plaintext.
- Heartbeat every 30 seconds; mark degraded after two misses and offline after three (about 90 seconds). Display last contact/event and queue/connection health.
- Offline queue: encrypted and bounded at 256 MiB per device. At the cap, pause lower-priority collection and report a visible gap; do not silently discard queued evidence. Use capped exponential backoff with jitter and never bypass TLS validation.
- Events preserve a stable event ID, device ID, device timestamp, server receipt timestamp, and server order/sequence. Database uniqueness enforces deduplication. Clock skew is visible; device time is not treated as trusted server time. Process identity is composite: device ID + PID + process start identity, because PIDs repeat across devices and over time.
- The owner approves collection scope and retention before collection starts. No file contents, environment variables, or broad filesystem scope by default. Revoking an inspector stops access without deleting owner data; revoking a device stops new ingestion, with historical data governed by owner retention.
- Before any pilot, add per-device signed event batches, a digest chain, and monotonic signed checkpoints stored by a signer/archive outside the production app, database, VM, and cloud credentials. The archive must reject rewrites/deletes, enforce sequence/previous-checkpoint continuity, and retain encrypted event batches or sufficient material to verify them. Verify the chain/checkpoint before exports and include integrity status, gaps, and clock warnings in the export manifest. Test database tampering, production-credential compromise, and archive recovery. This detects post-ingest changes under those trust assumptions; it cannot prove events are truthful if the target/collector is compromised, and it does not establish legal chain of custody.
- Audit grants, revocations, collection-scope changes, investigation access, exports, deletion, and administrative actions with actor, tenant, device/investigation, server timestamp, action, and request ID.

### Pilot and operations targets

- Initial pilot envelope: at most three owners and five devices. No uptime guarantee on the free, single-VM setup.
- Prototype recovery target: RPO up to 24 hours and RTO up to 8 hours. Encrypted backups go to OCI Object Storage separate from the VM, with restricted credentials, quota alerts, and an independently controlled archive copy not accessible with production credentials. The free object-storage quota is limited; verify current limits before provisioning: [OCI Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).
- Measure representative five-device latency/throughput first; set the numeric performance target only after the baseline. Do not assume the previously proposed five-second target.
- Require staging failure-injection tests across all 16 scenarios, normal regression tests, frontend build, dependency checks, cross-tenant authorization checks, restore, and rollback before pilot. Record actual versions and results; every untested or failing scenario blocks pilot.

### Decision log

| Date | Decision | Alternatives considered | Reason |
|---|---|---|---|
| 2026-11-02 | Shared MySQL with tenant scoping | Database per owner; deployment per owner | Fits the free-host prototype; every access path must be tenant-scoped and tested. |
| 2026-11-02 | Existing unowned data stays admin-only | Assign legacy data to a new owner | No trustworthy ownership mapping exists. |
| 2026-11-02 | Owner-approved inspector grants; read-only by default; export separately granted | Shared workspace or default export rights | Minimize disclosure and preserve owner control. |
| 2026-11-02 | Invite-only pilot; named project operator | Public signup; separate operator | Reduce abuse while tenant and recovery controls are proven. |
| 2026-11-02 | Windows, Linux, and macOS collector support | Windows-only first | Required platform scope; protected queue/key backends must be OS-specific and fail closed. |
| 2026-11-02 | 30-second heartbeat; offline at about 90 seconds | Faster/slower heartbeat | User-selected initial health signal; validate on sleeping/offline devices. |
| 2026-11-02 | Owner chooses retention before collection | Automatic 30/90-day default | Avoid silent retention of sensitive telemetry. |
| 2026-11-02 | 256 MiB encrypted queue/device; pause and report gaps at cap | Drop oldest; unbounded queue | Bounded storage without silent loss. |
| 2026-11-02 | RPO 24h / RTO 8h for prototype | RPO 1h / RTO 4h | Fits the selected prototype target; must be proven by restore drills. |
| 2026-11-02 | Measure performance first, then set target | Preset p95 <5s | Avoid an unsupported latency promise. |
| 2026-11-02 | Signed event-chain checkpoints before pilot | Basic database audit table only | User requires stronger integrity controls before pilot; no legal chain-of-custody claim. |
| 2026-11-02 | Independent signer/archive outside production credentials and VM required before pilot | Checkpoint key/archive in same app account | User selected an independent signer/archive after design review identified that same-account keys do not cover production-account compromise. |
| 2026-11-02 | Process identity uses device + PID + process start identity | PID-only process key | PIDs collide across devices and are reused over time. |
| 2026-11-02 | All privileged/global routes remain tenant-scoped; no implicit admin data access | Admin bypass across tenant boundaries | Prevent SQL console, global metrics, bridge, audit, or admin endpoints from bypassing owner isolation. |
| 2026-11-02 | OS-specific protected key stores; fail closed when unavailable | Plaintext queue/credential fallback | Cross-platform durable queue must not expose credentials or telemetry at rest. |
| 2026-11-02 | Tenant security → event protocol → privacy/integrity → operations → full test gate | Deployment-first/happy-path-first | Reduces exposure before collector onboarding and public deployment. |

## Deployment sequence (not yet executed)

### Phase 1 — Confirm hosting details

- Select the OCI home region and confirm current Always Free capacity without enabling paid resources.
- Select the public DNS hostname and verify TLS issuance is possible for it.
- Confirm the named operator has access to the account, secrets, and independent backup destination.
- Confirm that an ARM64 OCI VM can run the project's images and Python/Node dependencies; the current Compose stack has not been validated on OCI ARM64.

### Phase 2 — Prepare the application for remote use

- Add tenant/device ownership and API-level authorization before inviting external users.
- Implement device registration, per-device credential rotation/revocation, and owner approval.
- Add collector configuration that securely sets the public HTTPS server URL and device credential; ensure installer/service startup preserves these settings without writing secrets into a tracked config file.
- Configure Compose for public deployment: backend not publicly exposed, MySQL private, persistent volume protected, reverse proxy/TLS, health checks, restart policy, and safe resource limits.
- Review public API behavior, rate limiting, body-size enforcement, CORS, headers, logs, and error messages.
- Implement the 16 scenarios above, then run backend tests, frontend production build, dependency/security checks, and collector-to-cloud smoke tests. Record actual results; do not publish assumed pass counts.

### Phase 3 — Provision free host and HTTPS

- Create the OCI Always Free VM in the selected home region and check current capacity/limits. Do not enable paid resources or upgrade the account without explicitly agreeing to costs.
- Configure SSH keys, host firewall, automatic security updates, and restricted administrative access.
- Point the chosen DNS hostname to the VM. Configure Caddy (or equivalent) for HTTPS and redirect HTTP to HTTPS.
- Configure host firewall so only required public ports are reachable. Keep SSH restricted; do not publish MySQL or the backend port.
- Store secrets on the VM with restrictive permissions. Generate unique production values for database credentials, admin password, JWT key, and device credentials. Never commit them or paste them into chat.

### Phase 4 — Deploy and validate

- Back up any existing database before schema or account changes. Confirm the deployment schema and MySQL app-user grants.
- Start the services and confirm health checks, TLS, admin login, API auth, database persistence across restart, and frontend-to-API routing.
- Enroll one consenting test machine. Confirm its owner identity, assigned device, approved collection scope, event timestamps, host ID, and ability to revoke and stop collection.
- Confirm no other user can see the device's data by attempting negative authorization checks.
- Run every failure-injection scenario in staging. Test backup restoration and document recovery/rollback steps before considering production readiness. A happy-path smoke test is insufficient.

### Phase 5 — Operate within free limits

- Monitor VM availability, storage growth, service logs, certificate renewal, and provider notifications.
- Export encrypted backups off the VM on a defined schedule and test restoring them. Keep the backup key separate from the server.
- Document provider free-tier changes and review this plan when hosting limits, legal requirements, users, or collection scope change.
- Move to paid or customer-controlled infrastructure before the free-tier reliability/retention limits conflict with the investigation's needs.

## Decisions recorded

| Decision | Current position |
|---|---|
| No localhost-only deployment | Required. The web application and API must have a public HTTPS endpoint. |
| Remote system visibility | Requires an explicitly authorized host collector/agent; a website cannot inspect a remote host by itself. |
| Free hosting preference | OCI Always Free VM running Docker Compose is the first prototype candidate, subject to ARM64 validation and account capacity. |
| Frontend/API/database placement | Keep all three on the same VM initially; expose through one TLS hostname, keep MySQL private. |
| Multi-owner public service | Not ready until tenant isolation, owner consent, and per-device access controls are implemented. |
| Forensic evidence guarantee | Current product does not promise tamper-evident chain of custody; do not represent it as such. |
| Failure readiness | The 16-scenario matrix is mandatory; every item must have evidence of a passing test before production. Current status: none verified. |
| Deployment execution | Not started. No account, VM, DNS, secret, database, or public service has been created or changed. |

## Change log

| Date | Change |
|---|---|
| 2026-11-01 | Created the plan around remote authorized collection, zero recurring hosting cost, OCI Always Free as the prototype candidate, and the current tenant-isolation/evidence-integrity limitations. |
| 2026-11-01 | Added the mandatory 16-scenario reliability/security/evidence release gate, explicit NOT VERIFIED test states, recovery/rollback expectations, and NIST SP 800-61 Rev. 3 reference. |
| 2026-11-01 | Added a dependency-ordered remediation roadmap and source-based baseline distinguishing partial controls from end-to-end guarantees. |
| 2026-11-02 | Recorded confirmed tenant/inspector rules, legacy-data handling, five-device pilot cap, three collector OSes, owner-selected retention, queue/heartbeat/recovery targets, integrity checkpoints, and implementation order. |
| 2026-11-02 | Added independent signer/archive requirement, process composite identity, privileged-route tenant checks, and per-OS protected credential modes after design review. |
| 2026-11-02 | Started tenant/device foundations: added workspace, invitation, device, credential and grant schema/routes; bound OS event ingest to active per-device credentials and device/workspace IDs; made source-event IDs deduplicate database inserts; removed shared-agent-token configuration. Existing legacy reads are still globally scoped and block pilot readiness. |
| 2026-11-02 | Verification checkpoint: `git diff --check` passed. Application/test execution remains pending because Docker Desktop's Linux engine is unavailable; the security-audit isolation requirement prohibits running project code/tests directly on the host. All 16 release scenarios remain NOT VERIFIED. |

## Sources checked for free-tier constraints

- [Oracle Cloud Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle Cloud Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
- [Render free services and data limits](https://render.com/docs/free)
- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Vercel Hobby plan](https://vercel.com/docs/plans/hobby)
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final)
- [NIST incident response overview](https://csrc.nist.gov/projects/incident-response)
