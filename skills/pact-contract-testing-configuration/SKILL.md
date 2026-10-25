---
name: pact-contract-testing-configuration
description: >
  Sets up consumer-driven contract testing with Pact — writing consumer
  contract tests that generate a pact file, standing up and configuring a
  Pact Broker (or PactFlow) to publish and share contracts, and writing
  provider verification tests against the broker's published pacts. Use
  when the user asks to "set up Pact contract testing," "write a consumer
  pact test," "configure a Pact Broker," "verify a provider against
  published contracts," or "add contract testing between these two
  services."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: iac-and-automation-tooling
  maturity: stable
---

# Pact Contract Testing Configuration

## Purpose

Integration bugs between independently-deployed services are usually
caught either too late (a full end-to-end environment, slow and flaky) or
not until production (no integration testing at all beyond unit tests with
mocked assumptions that silently drift from reality). Consumer-driven
contract testing with Pact closes that gap without a full integration
environment: the consumer of an API defines, as an executable test, the
exact interactions it depends on; that expectation is captured as a
"pact" file and published to a shared broker; the provider then verifies,
in its own CI, that it actually satisfies every consumer's published
expectations. This skill covers writing the consumer and provider tests
and standing up the broker that connects them — using those contracts to
gate deploys is covered separately in
[pact-configuration-validation](../pact-configuration-validation/SKILL.md).

## When to use

- Two or more independently-deployed services communicate over an API
  (HTTP/REST, GraphQL, or an async message format) and integration bugs
  between them are only caught in a slow shared staging environment or in
  production.
- Writing a new consumer-side contract test that specifies exactly what
  request/response shape a client expects from a provider.
- Writing a provider verification test/task that checks the provider's
  actual behavior against contracts published by its consumers.
- Standing up a Pact Broker (self-hosted or PactFlow) as the shared
  source of truth for contracts across multiple consumer/provider teams.
- Deciding whether a given interaction is a good candidate for contract
  testing versus full end-to-end testing.

## Prerequisites & environment

- A Pact client library for the consumer's language (`pact-js`,
  `pact-python`, `pact-jvm`, etc.) added to the consumer's test
  dependencies, and a corresponding library on the provider side for
  verification.
- A running Pact Broker — self-hosted (`pactfoundation/pact-broker` "docker
  image, backed by PostgreSQL) or the hosted PactFlow service — reachable
  from both the consumer's and provider's CI pipelines.
- CI pipelines for both the consumer and provider repos capable of
  publishing pact files and running provider verification as a distinct
  step — see
  [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md)
  for where this step fits in an overall pipeline.
- Agreement between consumer and provider teams on ownership: who
  maintains the broker, who is notified when a contract changes, and what
  happens when provider verification fails (this is largely a
  cross-team process question, not just a tool-configuration one).

## Step-by-step guidance

1. **Write the consumer test against a Pact mock provider**, describing
   the exact interaction the consumer depends on — not a loose "any
   response shape," but the specific fields the consumer's code actually
   reads:
   ```javascript
   // pact-js, consumer side: order-service consuming inventory-service
   const { PactV3, MatchersV3 } = require('@pact-foundation/pact');
   const { like, integer } = MatchersV3;

   const provider = new PactV3({ consumer: 'order-service', provider: 'inventory-service' });

   describe('GET /inventory/:sku', () => {
     it('returns current stock level', () => {
       provider
         .given('sku ABC123 exists with stock 42')
         .uponReceiving('a request for current stock')
         .withRequest({ method: 'GET', path: '/inventory/ABC123' })
         .willRespondWith({
           status: 200,
           body: { sku: 'ABC123', stock: integer(42) },
         });

       return provider.executeTest(async (mockServer) => {
         const client = new InventoryClient(mockServer.url);
         const result = await client.getStock('ABC123');
         expect(result.stock).toEqual(42);
       });
     });
   });
   ```
   Running this test both verifies the consumer's own code against the
   mock and generates a pact file (JSON) capturing the interaction.

2. **Publish the generated pact file to the broker** as part of the
   consumer's CI pipeline, tagged with a version identifier that ties it
   back to a real deployable artifact (commit SHA or build number, not a
   loose "latest"):
   ```bash
   pact-broker publish ./pacts \
     --consumer-app-version="$(git rev-parse --short HEAD)" \
     --branch="$(git rev-parse --abbrev-ref HEAD)" \
     --broker-base-url="$PACT_BROKER_URL" \
     --broker-token="$PACT_BROKER_TOKEN"
   ```
   Tagging by branch (in addition to version) lets the broker track
   which contract version is "the one currently on `main`" versus a
   feature branch's in-progress contract.

3. **Write the provider verification test**, pointing at the broker
   instead of a static local pact file, so it always verifies against
   the latest published consumer expectations:
   ```javascript
   // pact-js, provider side: inventory-service verifying against all
   // consumer contracts published to the broker
   const { Verifier } = require('@pact-foundation/pact');

   new Verifier({
     provider: 'inventory-service',
     providerBaseUrl: 'http://localhost:3001',
     pactBrokerUrl: process.env.PACT_BROKER_URL,
     pactBrokerToken: process.env.PACT_BROKER_TOKEN,
     publishVerificationResult: true,
     providerVersion: process.env.GIT_COMMIT,
     stateHandlers: {
       'sku ABC123 exists with stock 42': async () => {
         await seedTestDb({ sku: 'ABC123', stock: 42 });
       },
     },
   }).verifyProvider();
   ```
   `stateHandlers` implement the `.given(...)` provider states declared
   by consumer tests — the provider verification run must actually put
   its test environment into that state before replaying the request,
   not just check the response shape against a mock.

4. **Publish verification results back to the broker**
   (`publishVerificationResult: true` above) so the broker has a
   complete, queryable picture of which provider version satisfies which
   consumer contract version — this is the data
   [pact-configuration-validation](../pact-configuration-validation/SKILL.md)'s
   `can-i-deploy` check reads from.

5. **Stand up the broker itself** if self-hosting rather than using
   PactFlow, backed by a real database (not the broker's default SQLite,
   which isn't intended for team/production use):
   ```yaml
   # docker-compose.yml excerpt
   services:
     pact-broker:
       image: pactfoundation/pact-broker:latest
       environment:
         PACT_BROKER_DATABASE_URL: "postgres://pact:${PACT_DB_PASSWORD}@postgres/pactbroker"
         PACT_BROKER_BASIC_AUTH_USERNAME: "${PACT_BROKER_USER}"
         PACT_BROKER_BASIC_AUTH_PASSWORD: "${PACT_BROKER_PASSWORD}"
       ports:
         - "9292:9292"
   ```
   Put the broker behind the same access controls as any other internal
   service that holds API contract details, and back its database up
   like any other stateful service.

6. **Choose contract testing deliberately, not for every interaction.**
   It fits well for synchronous request/response APIs and message-based
   integrations between services with clear consumer/provider roles; it
   fits poorly as a replacement for testing genuinely emergent, multi-hop
   system behavior (which still needs some end-to-end coverage) or for
   interactions where the "provider" is a third-party API you don't
   control and can't run verification against.

## Best practices

- Version pact files by the consumer's real deployable artifact version
  (commit SHA/build number), never a floating "latest," so the broker's
  compatibility matrix is trustworthy.
- Keep provider states (`stateHandlers`) realistic and isolated — each
  state should set up exactly the data needed for that interaction and
  clean up afterward, so verification runs are independent and
  repeatable.
- Write consumer expectations using matchers (`like`, `integer`, `term`)
  for values that can legitimately vary, not hardcoded exact values,
  unless the exact value truly matters — over-strict contracts break on
  every trivial provider change.
- Give the broker's webhook feature (triggering a provider verification
  build automatically when a consumer publishes a new contract) real
  attention early — without it, contract drift is only caught whenever
  the provider next happens to run CI, not when it should be, right
  after the consumer's change.
- Treat the pact broker like any other piece of shared infrastructure
  with an owner, backups, and access control — not an unowned side
  project that quietly becomes load-bearing.

## Common pitfalls

- **Symptom:** A provider verification build passes even though the
  provider recently changed a response field the consumer actually
  depends on.
  **Fix:** Check whether the consumer's contract used an overly loose
  matcher (or no matcher) for that field — a contract that doesn't
  actually assert on the field the consumer reads can't catch a
  regression in it; tighten the consumer test's expectations (step 1).

- **Symptom:** Provider verification fails with "no matching provider
  state handler" for a state the consumer test declared.
  **Fix:** The provider's `stateHandlers` map is missing (or misspelled
  relative to) that exact state string — state strings must match
  character-for-character between consumer `.given(...)` calls and
  provider `stateHandlers` keys (step 3).

- **Symptom:** The broker accumulates hundreds of pact versions from
  feature branches, and it's unclear which one reflects what's actually
  running in production.
  **Fix:** Publish with both a version (commit SHA) and a branch tag, and
  use the broker's "deployed"/"released" version-recording API
  (`pact-broker record-deployment`) to mark which specific version is
  actually live in each environment — this is exactly what
  [pact-configuration-validation](../pact-configuration-validation/SKILL.md)'s
  `can-i-deploy` check relies on to give a meaningful answer.

- **Symptom:** A team stands up Pact for a genuinely complex, multi-hop
  workflow and finds contract tests don't catch the actual bugs they
  were hoping to catch.
  **Fix:** Contract testing verifies pairwise consumer/provider
  interactions, not full end-to-end system behavior across many hops —
  keep some real end-to-end/integration coverage for genuinely emergent,
  multi-service behavior (step 6) rather than expecting Pact to replace
  it entirely.

## Worked example

**Scenario:** `order-service` (consumer) depends on `inventory-service`
(provider) for stock lookups; a recent production incident happened
because inventory-service changed a field name without order-service
noticing until deploy.

1. `order-service`'s CI adds the consumer test from step 1, generating a
   pact file describing the `GET /inventory/:sku` interaction with a
   `stock` field matched as `integer(42)` (any integer, not exactly 42).
2. On merge to `main`, `order-service`'s pipeline publishes the pact to
   the team's self-hosted broker, tagged with the merge commit SHA and
   branch `main`.
3. The broker's webhook fires a build in `inventory-service`'s CI,
   running the provider verification test from step 3 against the newly
   published contract, seeding test data via the `stateHandlers` map.
4. Verification passes and is published back to the broker
   (`publishVerificationResult: true`), giving the broker a record: "this
   `inventory-service` commit satisfies this `order-service` contract
   version."
5. Weeks later, an engineer on `inventory-service` renames the `stock`
   field to `quantity` in a draft PR. The next provider verification run
   (triggered automatically by the broker webhook on the existing
   published contract, since no new consumer contract was published)
   fails immediately — the mismatch is caught in `inventory-service`'s
   own CI before merge, not after both services are deployed together.

## Cross-references

- [pact-configuration-validation](../pact-configuration-validation/SKILL.md) —
  using the broker's compatibility data set up here to gate deploys with
  `can-i-deploy`, rather than only running verification informationally.
- [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md) —
  where the publish/verify steps fit as pipeline stages/gates for both
  the consumer and provider repos.
- [environment-promotion-strategy](../../../devops/skills/environment-promotion-strategy/SKILL.md) —
  recording which contract version is deployed to which environment,
  which the broker's deployment-tracking API depends on.
