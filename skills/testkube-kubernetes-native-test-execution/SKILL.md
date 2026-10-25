---
name: testkube-kubernetes-native-test-execution
description: >
  Runs test suites (Postman/Newman, k6, Cypress, Playwright, JMeter, and
  other supported executors) as Kubernetes-native `Test`/`TestSuite`
  (or `TestWorkflow`) custom resources via Testkube, executing tests
  inside the cluster against in-cluster services and wiring results back
  into CI. Use when the user asks to "run k6 load tests in Kubernetes,"
  "define a Testkube Test CRD," "run Postman collections against an
  in-cluster service," "chain multiple test types into a TestSuite," or
  "wire Testkube into a CI pipeline." Distinct from running the same
  test tools directly inside a CI runner (GitHub Actions/Jenkins/GitLab
  CI), which cannot reach in-cluster-only services without extra network
  plumbing.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: kubernetes-platform
  maturity: stable
---

# Testkube Kubernetes-Native Test Execution

## Purpose

A CI runner (a GitHub Actions job, a Jenkins agent) executes outside the
cluster by default — reaching an in-cluster-only service (one with no
public Ingress, addressable only via its `ClusterIP`/internal DNS name)
requires port-forwarding, a VPN hop, or a temporary Ingress just for the
test run, all of which are extra plumbing that drifts from what actually
runs in production. Testkube inverts this: it installs an operator and
CRDs (`Test`, `TestSuite`, and, in newer versions, the more general
`TestWorkflow`) into the cluster itself, so a test (a Postman/Newman
collection, a k6 load test, a Cypress/Playwright E2E suite, a JMeter
plan, or a custom script) runs as a **pod inside the cluster**, with
direct network access to the same internal services, Secrets, and
ConfigMaps the application itself uses — no port-forward, no temporary
Ingress, no VPN. Test executions, results, and logs become Kubernetes
objects (`Execution`s) queryable via `kubectl`/the Testkube CLI/API, not
just CI console output that disappears when the job ends. This skill
covers authoring `Test`/`TestSuite` resources and wiring them into CI;
the resulting workload-scaling behavior under a Testkube-driven load test
is a good input to
[keda-configuration-validation](../keda-configuration-validation/SKILL.md)'s
threshold checks, but that validation itself is out of scope here.

## When to use

- Running a k6 load test against an internal service's `ClusterIP`
  address without exposing it publicly or setting up a port-forward.
- Running a Postman/Newman API test collection against a service
  deployed into a namespace, as part of a post-deploy smoke test.
- Running a Cypress/Playwright E2E suite against an application running
  inside the cluster (e.g. in an ephemeral preview namespace per pull
  request).
- Chaining multiple test types (API test, then load test, then E2E) into
  a single ordered `TestSuite` run, rather than juggling separate CI job
  definitions for each tool.
- Triggering test execution from a CI pipeline (GitHub Actions, Jenkins,
  GitLab CI) via the Testkube CLI or API, so the CI job itself stays a
  thin trigger/poll-for-result step rather than needing every test
  tool's runtime installed on the CI runner.
- Running tests on a schedule (nightly regression, periodic synthetic
  monitoring) independent of any CI pipeline trigger.

## Prerequisites & environment

- A Kubernetes cluster with the Testkube operator and CRDs installed
  (commonly via the `kubeshop/testkube` Helm chart or the Testkube CLI's
  `testkube init`), which installs the API server, the executor
  controller, and (optionally) a MinIO/S3-backed artifact store for test
  logs and results.
- The Testkube CLI (`kubectl testkube` plugin or standalone `testkube`
  binary) installed wherever tests are triggered from — a developer
  machine or the CI runner.
- Network policy in the cluster that permits Testkube's executor pods to
  reach the services under test — the same namespace-scoped
  `NetworkPolicy` review that applies to any other in-cluster workload;
  a default-deny policy that doesn't account for Testkube's executor
  pods will make every test fail with a connection error that looks like
  an application bug.
- Test artifacts (Postman collection JSON, k6 script, Cypress/Playwright
  project) available either as a Git reference Testkube can clone, or
  bundled into a `ConfigMap`/custom test-runner image, depending on
  executor and repository size.
- For CI integration: a service account/API token scoped to trigger and
  read `Execution` results, not a cluster-admin credential handed to the
  CI runner.

## Step-by-step guidance

1. **Define a `Test` CRD for a single test type**, referencing the test
   content and specifying the executor:
   ```yaml
   apiVersion: tests.testkube.io/v3
   kind: Test
   metadata:
     name: checkout-api-smoke
     namespace: testkube
   spec:
     type: postman/collection
     content:
       type: git
       repository:
         uri: https://github.com/example-org/checkout-api-tests.git
         branch: main
         path: collections/smoke.postman_collection.json
     executionRequest:
       variables:
         BASE_URL:
           value: http://checkout-api.checkout.svc.cluster.local:8080
           type: basic
       negativeTest: false
   ```
   `BASE_URL` points at the service's **internal cluster DNS name**, not
   a public endpoint — this is the core advantage over running the same
   Postman collection from a CI runner, which would need that service
   exposed externally or a tunnel into the cluster to reach it at all.

2. **Define a k6 load test the same way**, for load/performance testing
   against an in-cluster target:
   ```yaml
   apiVersion: tests.testkube.io/v3
   kind: Test
   metadata:
     name: checkout-api-load
     namespace: testkube
   spec:
     type: k6/script
     content:
       type: git
       repository:
         uri: https://github.com/example-org/checkout-api-tests.git
         branch: main
         path: k6/checkout-load.js
     executionRequest:
       variables:
         TARGET_URL:
           value: http://checkout-api.checkout.svc.cluster.local:8080/checkout
           type: basic
         VUS:
           value: "50"
         DURATION:
           value: "5m"
   ```
   Running this inside the cluster means the load test's own network hop
   to the target is the same internal-service-to-internal-service path
   real production traffic between microservices takes — a load test run
   from outside the cluster instead measures the cluster's Ingress/LB
   path, which is a different (and often more favorable) bottleneck
   profile.

3. **Chain multiple `Test`s into an ordered `TestSuite`** so a release
   validation runs API checks, then load, then E2E in sequence rather
   than as separate uncoordinated CI jobs:
   ```yaml
   apiVersion: tests.testkube.io/v2
   kind: TestSuite
   metadata:
     name: checkout-release-validation
     namespace: testkube
   spec:
     steps:
       - execute:
           - test: checkout-api-smoke
       - execute:
           - test: checkout-api-load
       - execute:
           - test: checkout-e2e-cypress
     executionRequest:
       variables:
         BASE_URL:
           value: http://checkout-api.checkout.svc.cluster.local:8080
           type: basic
   ```
   Steps run in order; each step's `execute` list can contain multiple
   tests run in parallel within that step, with the suite as a whole
   failing if any required step fails — model this the same way a
   CI pipeline's sequential stages of parallel jobs are modeled in
   [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md).

4. **Trigger execution manually or via CLI** to validate the definitions
   before wiring them into CI:
   ```bash
   kubectl testkube run test checkout-api-smoke --namespace testkube -f
   kubectl testkube run testsuite checkout-release-validation --namespace testkube -f
   ```
   The `-f` flag follows execution logs live; omit it to trigger
   asynchronously and poll status separately with
   `kubectl testkube get execution <execution-id>`.

5. **Wire test execution into CI as a thin trigger-and-poll step**,
   keeping the CI runner itself free of every test tool's runtime
   (GitHub Actions example; the same CLI invocation works from Jenkins,
   GitLab CI, or any other runner with `kubectl`/cluster access):
   ```yaml
   # .github/workflows/post-deploy-validation.yml
   jobs:
     run-testkube-suite:
       runs-on: ubuntu-latest
       steps:
         - name: Configure kubeconfig
           run: echo "${{ secrets.KUBECONFIG_B64 }}" | base64 -d > $HOME/.kube/config
         - name: Install Testkube CLI
           run: curl -sSLf https://get.testkube.io | sh
         - name: Run release validation suite
           run: |
             kubectl testkube run testsuite checkout-release-validation \
               --namespace testkube -f --output-format json > result.json
         - name: Fail the job if the suite failed
           run: |
             jq -e '.status == "passed"' result.json
   ```
   The actual test tooling (k6, Newman, Cypress binaries/images) never
   needs to be installed on the CI runner — Testkube's executor images
   inside the cluster carry that, and the CI job only needs `kubectl`
   cluster access and the Testkube CLI.

6. **Scope the CI-facing credential to trigger and read executions only**,
   not broad cluster access:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: testkube-ci-trigger
     namespace: testkube
   rules:
     - apiGroups: ["tests.testkube.io", "testworkflows.testkube.io"]
       resources: ["tests", "testsuites", "testexecutions", "testsuiteexecutions"]
       verbs: ["get", "list", "create", "watch"]
   ```
   Bind this Role (not `cluster-admin`, and not even a broad namespace
   `edit` role) to the service account/token the CI pipeline
   authenticates with.

7. **For newer Testkube installations, consider `TestWorkflow`** instead
   of separate `Test`/`TestSuite` resources — it generalizes both into a
   single pipeline-style CRD with explicit steps, artifacts, and
   templates, which is the direction Testkube has been consolidating
   toward. Check which CRD version the installed Testkube operator
   actually supports before authoring against `TestWorkflow` syntax, since
   older operator versions only understand `Test`/`TestSuite`.

## Best practices

- Point tests at internal `ClusterIP`/cluster-DNS service addresses,
  not a public Ingress hostname — the in-cluster network path is
  Testkube's whole advantage over CI-runner-based testing, and testing
  through the public path defeats it while also adding an unnecessary
  external dependency to the test run.
- Keep the CI-facing Testkube credential scoped to trigger/read
  executions only (step 6), the same least-privilege discipline applied
  to any other CI service account in this repo.
- Store test artifacts (Postman collections, k6 scripts, Cypress specs)
  in version control referenced via the `git` content type, not pasted
  inline into the CRD, so test changes go through the same PR review as
  application code.
- Run a smoke-test `TestSuite` immediately after every deploy (wired
  into the same pipeline that performs the deploy) rather than only on a
  separate nightly schedule — catching a broken deploy within minutes is
  far cheaper than discovering it the next morning.
- Set resource requests/limits on executor pods (via the `Test`
  spec's job template, where the executor supports it) — an
  unconstrained load-test executor pod (k6 with a high `VUS` count) can
  itself consume enough cluster resources to starve the very services
  it's testing, producing misleading results.
- Feed a Testkube-driven k6 load test's measured throughput back into
  [keda-configuration-validation](../keda-configuration-validation/SKILL.md)'s
  per-replica capacity checks — an in-cluster load test is a more
  realistic capacity signal than a synthetic guess.

## Common pitfalls

- **Symptom:** A `Test` execution fails with a connection timeout/refused
  error reaching the target service, even though the service is
  confirmed healthy via `kubectl port-forward`.
  **Fix:** Check for a `NetworkPolicy` in the target namespace that
  default-denies ingress from other namespaces (including Testkube's
  executor namespace) — the executor pod runs as a normal in-cluster
  pod subject to the same network policy as anything else, and a
  default-deny policy that never accounted for Testkube will block it
  even though manual `port-forward` access (which bypasses in-cluster
  networking) works fine.

- **Symptom:** A k6 load test run via Testkube reports much better
  latency numbers than what real users/CI-external load tests observe
  against the same service.
  **Fix:** Confirm the test's `TARGET_URL` actually points at the
  service's cluster-internal address, not a public Ingress/LB hostname —
  if it's internal, the results are measuring internal service-mesh
  latency, not what an external client experiences through Ingress/CDN/
  TLS termination; that's a legitimate and useful measurement, but it
  must be labeled as such rather than presented as end-user latency.

- **Symptom:** A CI pipeline step that triggers a Testkube `TestSuite`
  reports "success" even though one of the suite's later steps actually
  failed.
  **Fix:** Check the actual JSON/exit status of the *suite* execution,
  not just that the `kubectl testkube run` command itself returned exit
  code 0 (which it usually does even for a failed test run unless
  explicitly checked) — parse the result payload's status field (as in
  step 5's `jq -e` check) and fail the CI job explicitly on anything
  other than a fully-passed suite.

- **Symptom:** A load test's executor pod consumes enough CPU/memory to
  cause the namespace's other pods (including the service under test)
  to be throttled or evicted, producing load-test results that reflect
  resource contention rather than the target service's real capacity.
  **Fix:** Set explicit resource requests/limits on the executor pod
  template and, for anything beyond a light smoke test, run load tests
  in a dedicated namespace/node pool separate from the services being
  tested, so the test's own resource footprint doesn't contaminate the
  measurement.

- **Symptom:** Test execution history (`Execution` objects, logs,
  artifacts) grows unbounded in the `testkube` namespace over months,
  degrading API server list operations against that namespace.
  **Fix:** Configure Testkube's execution history retention/cleanup (via
  its Helm chart values or a scheduled cleanup job) to a bounded window,
  the same way `successfulJobsHistoryLimit`/`failedJobsHistoryLimit`
  bound Kubernetes `Job` history elsewhere in this repo's guidance.

## Worked example

**Scenario:** After every deploy of `checkout-api` to a namespace, the
team wants an automated smoke test (Postman), a brief load test (k6),
and — only for a full release, not every merge — an E2E suite (Cypress),
run in-cluster and gating whether the deploy pipeline proceeds to promote
the release.

`Test` definitions (`checkout-api-smoke` and `checkout-api-load` as
authored in steps 1–2 above), plus:
```yaml
apiVersion: tests.testkube.io/v3
kind: Test
metadata:
  name: checkout-e2e-cypress
  namespace: testkube
spec:
  type: cypress/project
  content:
    type: git
    repository:
      uri: https://github.com/example-org/checkout-api-tests.git
      branch: main
      path: e2e
  executionRequest:
    variables:
      CYPRESS_BASE_URL:
        value: http://checkout-web.checkout.svc.cluster.local:3000
        type: basic
```

`TestSuite` gating a full release (as authored in step 3), triggered
from the deploy pipeline's post-deploy stage:
```yaml
# GitHub Actions step, appended after the deploy job succeeds
- name: Run full release validation suite
  run: |
    kubectl testkube run testsuite checkout-release-validation \
      --namespace testkube -f --output-format json > result.json
    jq -e '.status == "passed"' result.json
```
If `checkout-api-smoke` or `checkout-api-load` fails, the suite stops
before running the (slower) Cypress E2E step, and the pipeline's
promotion-to-production stage is blocked by the non-zero `jq -e` exit
code — the same fail-fast principle as ordering a fast unit-test stage
before a slow integration-test stage in any other pipeline design.

## Cross-references

- [keda-configuration-validation](../keda-configuration-validation/SKILL.md) — using a Testkube-driven k6 load test's measured throughput as an input to validating KEDA scaling thresholds for the same service.
- [keda-event-driven-autoscaling-configuration](../keda-event-driven-autoscaling-configuration/SKILL.md) — the autoscaling configuration whose behavior a Testkube load test can be used to exercise and observe.
- [helm-chart-authoring](../helm-chart-authoring/SKILL.md) — packaging the Testkube operator installation and `Test`/`TestSuite` resources as a Helm chart alongside the application they test.
- [secure-cicd-gates](../../../devsecops/skills/secure-cicd-gates/SKILL.md) — where a Testkube-driven test gate fits relative to security scan gates in an overall pipeline.
- [github-actions-centralized-reusable-workflows](../../../cicd-tooling/skills/github-actions-centralized-reusable-workflows/SKILL.md) — centralizing the Testkube CLI trigger-and-poll step (step 5) as a reusable workflow shared across multiple services' pipelines.
