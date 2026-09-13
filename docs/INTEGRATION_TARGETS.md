# AgentProof — Integration Target Shortlist

Directly answers the "no real system integration" gap flagged as the biggest product blocker
before a first paying customer: AgentProof today verifies against exactly one system — its own
simulator. This document ranks 20 real enterprise applications that AI agents are already being
pointed at, by how easily each one could become a *real* `EvidenceAdapter` (app/adapter.py) —
i.e., how close each already comes to AgentProof's core requirement: **an independent, read-only
credential, separate from whatever credential the agent writes with, that can see the same data
the agent just touched.**

Sourced from each vendor's own current API/auth documentation (linked inline), not assumed from
memory — exact scope/role names should still be re-verified against the vendor's docs at
implementation time, since these programs change.

## What "plug and play" means here

A 1-5 score, weighted toward what actually determines integration effort for AgentProof
specifically — not general API quality:

| Score | Meaning |
|---|---|
| **5** | Native, granular read-only credential (e.g. a key scoped to "read" on specific resources, nothing else) with no admin ticket required to create one, self-serve sandbox, simple auth (API key or straightforward OAuth). |
| **4** | Granular read vs. write scoping exists and is self-serve, but OAuth consent/app-review adds a step. |
| **3** | Read-only access is possible but requires building a custom role/permission set first — doable by one admin in an afternoon, not a security review. |
| **2** | Read-only access requires meaningful platform-specific engineering (custom roles, entity-level authorization objects) — a real implementation task, not configuration. |
| **1** | Read-only access requires a dedicated integration user, multi-layer security setup, and typically IT/security sign-off before any read call works. |

## The shortlist

| # | Application | Category | How agents act on it today | AgentProof's evidence surface | Credential separation mechanism | Plug-and-play |
|---|---|---|---|---|---|---|
| 1 | **Stripe** | Payments | Agents issue refunds, create charges, update subscriptions | `GET /v1/charges`, `/v1/refunds`, `/v1/disputes` | [Restricted API keys](https://docs.stripe.com/keys/restricted-api-keys) — per-resource Read / Write / None, self-serve in dashboard | **5** |
| 2 | **GitHub** | Dev / code agents | Agents open PRs, merge code, close issues | REST/GraphQL read endpoints (PRs, commits, checks) | Fine-grained PATs — explicit read vs. write per repo, per permission, self-serve | **5** |
| 3 | **Shopify** | E-commerce | Agents process orders, refunds, inventory adjustments | Admin API `GET /orders`, `/refunds`, `/inventory_levels` | Scoped Admin API access tokens (`read_orders` vs `write_orders`, etc.), self-serve via custom/public app | **4** |
| 4 | **HubSpot** | CRM / marketing | Agents update deals, contacts, send sequences | CRM API `GET /crm/v3/objects/*` | OAuth with granular per-object read scopes, free developer/sandbox account | **4** |
| 5 | **Slack** | Communication | Agents post messages, update channels, notify users | Web API `conversations.history`, `conversations.info` | OAuth granular scopes (e.g. read vs. post separated), free sandbox workspace | **4** |
| 6 | **Zendesk** | Customer support | Agents resolve/update tickets, post replies | `GET /api/v2/tickets`, `/tickets/{id}/audits` | API token + role-scoped agent (read-only view role), free trial sandbox | **4** |
| 7 | **Zoho Books / Zoho CRM** | SMB ERP / CRM | Agents create invoices, update records | `GET /books/v3/invoices`, CRM `GET /crm/v8/*` | OAuth granular scopes per module, free developer account | **4** |
| 8 | **Jira / Atlassian** | Issue tracking / DevOps | Agents create/transition tickets, comment | REST API `GET /issue/{key}`, `/issue/{key}/changelog` | API tokens / OAuth 2.0 with granular scopes, free tier | **4** |
| 9 | **QuickBooks Online** | SMB accounting | Agents create invoices, record payments | `GET /v3/company/{id}/invoice`, `/payment` | OAuth 2.0 scopes, free sandbox company | **4** |
| 10 | **Intercom** | Customer support | Agents resolve conversations, tag users | REST API `GET /conversations/{id}` | OAuth app scopes, sandbox workspace | **4** |
| 11 | **Gmail / Google Workspace** | Email | Agents send emails, manage labels | Gmail API `messages.get` with a `.readonly` scope | OAuth 2.0 with dedicated read-only scopes; enterprise-wide rollout needs admin domain-wide delegation | **3** |
| 12 | **Microsoft 365 / Dynamics 365** | Productivity / CRM / ERP | Agents send mail, update CRM/ERP records | Microsoft Graph `GET` endpoints with `*.Read` permissions | Graph API supports separate `.Read` / `.ReadWrite` app permissions; admin consent adds a step | **3** |
| 13 | **DocuSign** | Contracts / e-signature | Agents send envelopes for signature | REST API `GET /envelopes/{id}`, `/envelopes/{id}/audit_events` | OAuth + sandbox ("developer") account; role model is coarser than resource-level read/write | **3** |
| 14 | **Twilio** | SMS / voice | Agents send SMS, place calls, notify customers | REST API `GET /Messages`, `/Calls` | Subaccounts give isolation; API keys authenticate but don't natively separate read/write on core resources | **3** |
| 15 | **Salesforce** | CRM | Agents update opportunities, cases, close deals | REST/Bulk API `GET /services/data/vXX/sobjects/*` | Connected App OAuth + a custom read-only Permission Set (object-level Read, no Create/Edit/Delete) — buildable by one admin; [details](https://help.salesforce.com/s/articleView?id=xcloud.connected_app_manage_oauth.htm) | **3** |
| 16 | **ServiceNow** | ITSM / incident management | Agents create/resolve incidents, update CMDB | Table API `GET /api/now/table/incident` | Custom ACL role scoped to Read on specific tables + a "Web service access only" integration user; [details](https://www.servicenow.com/community/platform-privacy-security-forum/read-only-service-accounts-for-integrations/m-p/3517128) | **3** |
| 17 | **Okta / Azure AD** | Identity & access management | Agents provision/deprovision accounts, reset access | Admin API `GET /users`, `/logs` (read-only API token or role) | Granular read vs. write API scopes exist technically, but identity-system read access typically triggers its own security review regardless of scope | **3** |
| 18 | **NetSuite** | ERP / finance | Agents post journal entries, create invoices | SuiteTalk REST `GET /record/v1/invoice` | Requires a custom "Web Services Only" role with object-level View-only permissions; [details](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/bridgehead_4248124361.html) — also mid-migration from token auth to OAuth 2.0 | **2** |
| 19 | **SAP (S/4HANA / SuccessFactors)** | ERP | Agents post transactions, update HR/finance records | OData services with read-only authorization objects | SAP's PFCG authorization-object model supports field/entity read-only roles, but the role-design process is enterprise-IT-owned and typically slow | **2** |
| 20 | **Workday** | HR / payroll | Agents process HR changes, payroll adjustments | RaaS (Report-as-a-Service) / REST read endpoints scoped by Functional Area | Requires a dedicated Integration System User (ISU) + security group + API Client functional-area scoping — two-layer permission system; [details](https://www.reco.ai/hub/workday-rest-api-integration-security) | **1** |

## Recommended build order

Given the actual gap (no second real `EvidenceAdapter` exists yet), and weighing plug-and-play
score against `docs/BUYER_PROFILE.md`'s segments (AI automation leads with a write-capable agent
already in production; fintech/payments ops as the wedge):

1. **Stripe** — highest plug-and-play score *and* the closest possible match to the already-built
   and already-demoed refund scenario. Almost no new evidence-adapter design work: the shape is
   identical to the simulator (`refund_exists`, `refund.status`, `refund.amount` → real Stripe
   equivalents). This is the obvious first real integration, not a new bet.
2. **GitHub** — highest score, and a strong second scenario for the Segment 1 buyer persona
   (AI automation / dev-tooling leads) who may find "did the agent's PR actually merge, and did
   CI actually pass" more relatable than a refund.
3. **Zendesk or Intercom** — either matches a very common real agent use case today (support
   ticket resolution) and both score a clean 4.
4. **Shopify** — a natural second fintech-adjacent wedge (order/refund verification for
   e-commerce specifically, distinct from Stripe's raw payments layer).

Hold off on Salesforce, ServiceNow, Okta/Azure AD, NetSuite, SAP, and Workday until a specific
paying customer asks for one by name — each requires either custom role engineering or a security
review cycle that isn't worth pre-building speculatively (this is the same "don't build ahead of
a real customer" discipline `docs/MVP_SCOPE.md` already applies to scenarios).

## What doesn't change

Per `docs/PROOF_MODEL.md`, adding a real adapter for any of these means writing one new
`EvidenceAdapter` implementation and registering it in `app.adapter.ADAPTER_REGISTRY` — it does
not require touching the verdict engine, the proof-definition format, or the claim normalizer.
That architectural claim was exactly what `duck/agent-sdk-independence-test.md` set out to
pressure-test on the *agent* side; a real second adapter would be the equivalent proof on the
*evidence* side, and is a natural next validation step once a specific customer names a system.
