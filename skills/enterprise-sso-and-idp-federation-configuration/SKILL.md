---
name: enterprise-sso-and-idp-federation-configuration
description: >
  Guides configuring enterprise workforce single sign-on — SAML 2.0 and
  OIDC federation between an identity provider (Okta, Azure AD/Entra ID,
  Keycloak) and downstream applications, including metadata exchange,
  attribute/claim mapping, group-to-role provisioning (SCIM), and
  multi-IdP federation trust. Use when the user asks to "set up SAML SSO
  with Okta," "configure Azure AD/Entra ID as our OIDC provider," "stand
  up Keycloak as an internal IdP," "map IdP groups to application roles,"
  "debug a SAML assertion that won't validate," or "federate a second
  IdP for an acquired company's users." Distinct from cloud-iam-hardening
  (workload/service IAM in a cloud provider) — this skill is about
  federating *human workforce* identity into applications for SSO.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: security-scanning-tooling
  maturity: stable
---

# Enterprise SSO and IdP Federation Configuration

## Purpose

Enterprise single sign-on lets a workforce authenticate once against a
central identity provider (IdP) and reach every downstream application
(a SaaS tool, an internal admin console, a Kubernetes dashboard) without
a separate password for each — but that convenience only holds up if the
federation trust between IdP and service provider (SP) is configured
correctly. A SAML assertion with the wrong `NameID` format, an OIDC
client with an overly permissive redirect URI, or a group-to-role
mapping that silently defaults new joiners to an admin role are not
cosmetic mistakes: they are authentication and authorization bypasses
hiding behind a working login screen. This skill covers configuring
SAML 2.0 and OIDC federation with the three IdPs most enterprises
actually run (Okta, Azure AD/Entra ID, Keycloak for self-hosted/hybrid
needs), exchanging and validating metadata, mapping IdP groups/claims to
application roles, provisioning via SCIM, and trusting a second IdP
(common after an acquisition or a multi-tenant B2B scenario). It is
distinct from [cloud-iam-hardening](../../../cloud/skills/cloud-iam-hardening/SKILL.md),
which covers a cloud provider's own IAM for workload/service identity —
this skill is squarely about *workforce* identity reaching applications
via SSO, not machine-to-machine or cloud-resource authorization.

## When to use

- Standing up SAML 2.0 SSO between an IdP (Okta, Azure AD/Entra ID,
  Keycloak) and a new SaaS or internally-built application acting as the
  service provider.
- Configuring OIDC (Authorization Code flow with PKCE) as the federation
  protocol instead of SAML for a modern application or API.
- Mapping IdP groups or claims to application-side roles/permissions
  (e.g. an Azure AD security group granting `admin` in a downstream
  tool), including deciding a safe default role for unmapped users.
- Setting up SCIM-based user/group provisioning so accounts are
  automatically created, updated, and deactivated in the downstream
  application as the IdP's directory changes.
- Federating a second IdP into an existing application — an acquired
  company's Azure AD tenant, a partner's Okta org, or a B2B customer's
  IdP — without disrupting the existing trust.
- Debugging a SAML assertion or OIDC token that fails to validate, an
  unexpected `NameID`/`sub` mismatch, or users landing with the wrong
  (or no) application role after a successful login.
- Deciding between SAML and OIDC for a new integration, or planning a
  migration from one to the other.

## Prerequisites & environment

- Admin access to the IdP's federation configuration (Okta application
  integrations, Azure AD/Entra ID Enterprise Applications, Keycloak
  realm/client admin console) and to the downstream application's SSO
  settings.
- A decision on protocol: **SAML 2.0** for older/enterprise SaaS that
  only supports it, or applications requiring rich XML-based assertions
  and IdP-initiated flows; **OIDC** (built on OAuth 2.0) for modern
  applications, APIs, and anything wanting JSON Web Tokens and simpler
  mobile/SPA support. Many IdPs (Okta, Azure AD, Keycloak) support both
  from the same directory — the choice is usually driven by what the
  downstream application/SP supports, not IdP capability.
- For SAML: the SP's metadata XML (ACS URL, Entity ID, and its public
  signing certificate if the SP also signs `AuthnRequest`s) and the IdP's
  metadata XML (SSO URL, Entity ID, IdP signing certificate) — exchanged
  before either side can validate the other.
- For OIDC: a registered client (`${OIDC_CLIENT_ID}` /
  `${OIDC_CLIENT_SECRET}`, or a public client with PKCE and no secret)
  at the IdP, and clarity on which flow — **Authorization Code with
  PKCE** for anything with a backend or a public client (SPA/mobile);
  never the deprecated Implicit flow for new integrations.
- SCIM 2.0 support on both IdP and downstream application if automated
  provisioning/deprovisioning is in scope — confirm the application's
  SCIM endpoint and bearer token before assuming group-based
  provisioning "just works" from IdP group membership alone.
- A non-production tenant/realm or a test application entry to validate
  the federation trust against before touching a production application
  that real employees depend on to log in.
- Keycloak ≥ 22 if self-hosting — realm export/import format and the
  admin REST API have changed across major versions; confirm the
  installed version's client-settings schema before reusing an older
  realm export.

## Step-by-step guidance

1. **Exchange metadata rather than hand-typing endpoint URLs** for SAML
   — metadata XML captures the Entity ID, SSO/ACS URLs, `NameID` format,
   and signing certificate in one machine-readable document, and manual
   transcription is a common source of subtly wrong URLs:
   ```xml
   <!-- IdP metadata excerpt (Okta/Azure AD/Keycloak all expose this) -->
   <EntityDescriptor entityID="https://idp.example.com/app/exkabc123/sso/saml/metadata">
     <IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
       <KeyDescriptor use="signing">
         <ds:X509Certificate>MIIDpDCCAoygAwIBAgIGAX...(truncated)</ds:X509Certificate>
       </KeyDescriptor>
       <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
         Location="https://idp.example.com/app/exkabc123/sso/saml"/>
     </IDPSSODescriptor>
   </EntityDescriptor>
   ```
   Upload this directly into the SP's "IdP metadata" field where
   supported, rather than copying individual fields by hand.

2. **Configure the SP-side application in the IdP** with the exact
   Assertion Consumer Service (ACS) URL and Entity ID/Audience the
   downstream application expects — a mismatched Audience is the single
   most common cause of a rejected assertion. Okta example (Application
   → SAML Settings):
   ```
   Single sign-on URL (ACS):  https://app.example.com/saml/acs
   Audience URI (SP Entity ID): https://app.example.com/saml/metadata
   Name ID format: EmailAddress
   Application username: Email
   ```

3. **Map IdP groups/attributes to application roles explicitly**, and
   decide a safe default for anyone not matched — never default to an
   admin or broad-access role:
   ```
   # Okta SAML attribute statements
   Name: groups
   Name format: Unspecified
   Filter: Matches regex ^(app-admin|app-viewer|app-editor)$
   ```
   ```yaml
   # Downstream application's role-mapping config (illustrative)
   role_mapping:
     app-admin: admin
     app-editor: editor
     app-viewer: viewer
   default_role: viewer   # never "admin" — least privilege for unmapped users
   ```
   > **Warning:** a default role of `admin` (or an implicit fallback
   > when no group matches) silently grants elevated access to any user
   > the IdP directory hasn't been explicitly and correctly grouped for
   > yet — including a new-joiner whose group assignment hasn't
   > propagated, or an off-boarded contractor whose group was removed
   > but who still authenticates successfully. Always default new/
   > unmapped users to the least-privileged role, or to no access with
   > an explicit request-access flow.

4. **For OIDC, register the client with a tightly scoped redirect URI
   and Authorization Code + PKCE**, not the Implicit flow:
   ```
   # Azure AD / Entra ID app registration
   Redirect URI: https://app.example.com/auth/callback   # exact match, no wildcard
   Supported account types: Single tenant (unless deliberate multi-tenant)
   Allow public client flows: No   # confidential client with a backend
   ```
   ```
   # Token request (Authorization Code + PKCE)
   POST /oauth2/v2.0/token
   grant_type=authorization_code
   code=<AUTH_CODE>
   redirect_uri=https://app.example.com/auth/callback
   client_id=${OIDC_CLIENT_ID}
   client_secret=${OIDC_CLIENT_SECRET}
   code_verifier=<PKCE_VERIFIER>
   ```
   A redirect URI with a wildcard or an overly broad path (e.g.
   `https://app.example.com/*`) lets an attacker who can host content
   under that domain redirect the authorization code to a page they
   control — scope it to the exact callback path.

5. **Validate claims/attributes the application actually receives**
   before trusting the integration — decode a real ID token or inspect a
   real SAML assertion rather than assuming the IdP config maps as
   expected:
   ```bash
   # Decode an OIDC ID token's payload (no verification, inspection only)
   echo "<JWT_PAYLOAD_SEGMENT>" | base64 -d | jq .
   ```
   ```json
   {
     "sub": "00u1a2b3c4d5e6f7g8h9",
     "email": "jane.doe@example.com",
     "groups": ["app-editor"],
     "iss": "https://idp.example.com/oauth2/default",
     "aud": "0oa1a2b3c4d5e6f7g8h9",
     "exp": 1735689600
   }
   ```
   Confirm `iss`/`aud` (OIDC) or `Issuer`/`Audience` (SAML) match exactly
   what the application validates against — a same-looking but
   trailing-slash-different issuer URL is a real, easy-to-miss mismatch.

6. **Set up SCIM provisioning** so directory changes (new hire, role
   change, termination) propagate automatically instead of relying on
   someone remembering to update the downstream app manually:
   ```http
   POST /scim/v2/Users
   Authorization: Bearer ${SCIM_BEARER_TOKEN}
   Content-Type: application/scim+json
   ```
   ```json
   {
     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
     "userName": "jane.doe@example.com",
     "active": true,
     "emails": [{ "value": "jane.doe@example.com", "primary": true }],
     "groups": [{ "value": "app-editor" }]
   }
   ```
   Confirm the IdP is configured to push a **deactivation** (`active:
   false` via `PATCH`) on termination, not just creation on hire — SCIM
   deprovisioning is the half of the integration most often left
   untested until an offboarding audit finds a terminated employee still
   able to log in.

7. **Federate a second IdP without disrupting the first**, scoping each
   IdP's trust to a specific domain/tenant or Identity Provider Routing
   Rule rather than a single ambiguous trust anyone could authenticate
   through:
   ```
   # Okta: Identity Provider Routing Rule
   IF user's email domain = "acquired-co.com"
   THEN route to IdP: acquired-co-azuread
   ELSE route to IdP: primary-okta
   ```
   Test the routing rule against both domains before rollout — an
   incorrectly ordered or overlapping rule can silently route a subset
   of the *existing* workforce to the wrong (or a not-yet-fully-
   provisioned) IdP.

8. **Rotate signing certificates on a scheduled, non-emergency basis**
   and support certificate rollover without an outage — both the IdP
   and SP-side certificates expire, and most protocols have no automatic
   graceful failover:
   ```
   # Configure the SP to accept two valid signing certs during rollover
   # (old + new), then remove the old one only after confirming the new
   # one is live and validating successfully.
   ```
   > **Warning:** letting a SAML IdP signing certificate expire
   > unnoticed breaks every SSO login for every application trusting
   > that IdP simultaneously — track certificate expiry as a monitored,
   > alerted date, not something discovered when login volume drops to
   > zero.

## Best practices

- Exchange metadata XML rather than hand-entering SSO URLs/Entity IDs —
  it's both faster and closes off an entire class of typo-driven
  mismatch.
- Always default unmapped users to the least-privileged role (or no
  access) rather than an admin/broad-access fallback — treat a broad
  default role as a standing security finding, not a convenience.
- Use Authorization Code + PKCE for every new OIDC integration; never
  stand up a new integration on the deprecated Implicit flow, and treat
  migrating an existing Implicit-flow integration as a priority, not
  optional cleanup.
- Scope OIDC redirect URIs and SAML ACS URLs to the exact expected path
  — no wildcards — since a broad redirect URI is a practical open
  redirect / authorization-code-theft vector.
- Test SCIM deprovisioning as rigorously as provisioning — an
  offboarding flow that silently fails to deactivate a downstream
  account is a standing access-control gap that often goes unnoticed
  for months.
- Track IdP and SP signing-certificate expiry dates as monitored,
  alerting events well ahead of expiry, and support certificate rollover
  (both old and new trusted simultaneously) rather than a hard cutover.
- Route a second/acquired-company IdP through explicit, tested routing
  rules (domain- or tenant-based) rather than an ambiguous trust that
  could let the wrong population authenticate through the wrong IdP.

## Common pitfalls

- **Symptom:** A SAML login redirects back from the IdP but the
  application rejects the assertion with an audience/issuer mismatch
  error, even though "everything looks right" in the console.
  **Fix:** Compare the exact string values — including trailing
  slashes and http vs. https — of the SP's configured Audience/Entity ID
  against what the IdP actually sends in the assertion (inspect the raw
  SAML response, e.g. via a browser SAML-tracer extension or the
  application's debug log), rather than assuming visually-similar values
  are identical.

- **Symptom:** A newly onboarded contractor logs in successfully and
  immediately has full admin access to the application, despite never
  being added to the "app-admin" IdP group.
  **Fix:** The role-mapping configuration has a default/fallback role
  set to `admin` (or the group filter/regex is too permissive and
  unintentionally matches an unrelated group name). Set the default
  role to the least-privileged option and tighten the group-matching
  filter, then audit any other user currently authenticated under the
  same broad default.

- **Symptom:** An employee is terminated and removed from the IdP
  directory, but can still successfully log in to a downstream
  SaaS application weeks later.
  **Fix:** SCIM deprovisioning either isn't configured for that
  application, or the IdP is only pushing group/attribute *updates*
  and not the `active: false` deactivation event. Verify the
  application's SCIM endpoint actually receives and acts on `PATCH
  .../Users/{id}` with `active: false`, and add offboarding
  verification as a routine, tested step — not an assumption.

- **Symptom:** SSO for every application trusting a given IdP breaks
  simultaneously, all at the same time, for no apparent configuration
  change.
  **Fix:** The IdP's SAML signing certificate expired. This is
  preventable by tracking certificate expiry as a monitored date well
  in advance and rotating with an overlap period (both old and new
  certs trusted) rather than reactively after every login starts
  failing.

- **Symptom:** After federating a second IdP for an acquired company,
  a subset of *existing* employees (not the acquired company's users)
  unexpectedly get routed to the new IdP and can't log in.
  **Fix:** The IdP routing rule's domain/condition match is too broad
  or ordered incorrectly (e.g. a catch-all rule evaluated before the
  more specific one). Test routing rules against representative emails
  from both populations before rollout, and order rules from most to
  least specific.

## Worked example

**Scenario:** Configure Okta as the primary IdP for an internal
`app.example.com` service via SAML, mapping Okta groups to application
roles, and adding SCIM provisioning — then federate a second IdP
(the acquired `acquired-co.com`'s Azure AD tenant) without disrupting
existing users.

1. Okta SAML application setup:
   ```
   Single sign-on URL (ACS): https://app.example.com/saml/acs
   Audience URI (SP Entity ID): https://app.example.com/saml/metadata
   Name ID format: EmailAddress
   Attribute statement: groups → filter matches ^(app-admin|app-editor|app-viewer)$
   ```

2. Application-side role mapping (`config/sso-roles.yaml`):
   ```yaml
   role_mapping:
     app-admin: admin
     app-editor: editor
     app-viewer: viewer
   default_role: viewer
   ```

3. SCIM provisioning enabled in Okta pointed at the app's SCIM endpoint:
   ```
   SCIM connector base URL: https://app.example.com/scim/v2
   Bearer token: ${SCIM_BEARER_TOKEN}
   Provisioning: Create, Update, Deactivate users — all three enabled
   ```
   A test termination in Okta (deactivating a test user) is verified to
   send a `PATCH` with `active: false`, and the application confirms the
   corresponding account is locked out, before enabling this for the
   full directory.

4. Six months later, `acquired-co.com` is acquired and its Azure AD
   tenant needs federated access to the same application without
   disrupting existing Okta-authenticated users. An Identity Provider
   Routing Rule is added:
   ```
   IF user's email domain = "acquired-co.com"
   THEN route to IdP: acquired-co-azuread (OIDC)
   ELSE route to IdP: primary-okta (SAML)
   ```
   Tested against `jane.doe@example.com` (routes to Okta, unaffected)
   and `sam.lee@acquired-co.com` (routes to the new Azure AD OIDC
   integration, using Authorization Code + PKCE), confirming both
   populations authenticate correctly before the rule goes live for all
   users.

## Cross-references

- [certificate-lifecycle-management-at-scale](../certificate-lifecycle-management-at-scale/SKILL.md) —
  tracking and rotating the SAML/OIDC signing certificates this
  federation trust depends on, across many applications at once.
- [vault-operations-and-pki-engine-configuration](../vault-operations-and-pki-engine-configuration/SKILL.md) —
  a comparable trust-chain/certificate-rotation discipline, applied to
  internal PKI rather than IdP federation certificates.
- [secrets-management](../../../devsecops/skills/secrets-management/SKILL.md) —
  where OIDC client secrets and SCIM bearer tokens should actually live
  (a secrets manager, not hardcoded application config).
- [cloud-iam-hardening](../../../cloud/skills/cloud-iam-hardening/SKILL.md) —
  the cloud-provider-native IAM/workload-identity side of access
  control, distinct from the workforce SSO federation this skill covers.
