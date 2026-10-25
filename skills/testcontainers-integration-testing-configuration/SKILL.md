---
name: testcontainers-integration-testing-configuration
description: >
  Guides configuring Testcontainers to spin up real dependency containers
  (Postgres, Kafka, Redis, and similar) for integration tests instead of
  mocks or hand-maintained shared test environments — container
  lifecycle management (per-test vs. shared/singleton containers),
  wait strategies, and CI runner resource/Docker-in-Docker
  considerations. Use when the user asks to "write an integration test
  against a real Postgres/Kafka/Redis container," "replace this mock
  with Testcontainers," "speed up a slow Testcontainers test suite," "run
  Testcontainers in CI," or "why does my Testcontainers test hang/fail
  only in the CI runner."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: iac-and-automation-tooling
  maturity: stable
---

# Testcontainers Integration Testing Configuration

## Purpose

A unit test that mocks the database driver proves the code calls the
mock correctly, not that it works against a real Postgres — a subtly
wrong SQL query, an index assumption that doesn't hold, or a
driver-specific type-mapping quirk routinely passes every mocked test
and fails only in a real environment. **Testcontainers** closes that gap
by programmatically starting real, disposable Docker containers (a real
Postgres, a real Kafka broker, a real Redis instance) scoped to a test
run, so integration tests exercise the actual dependency instead of a
stand-in for it — without a hand-maintained shared staging database that
tests can corrupt for each other or drift out of sync with production
versions. This skill covers container lifecycle management (per-test vs.
module-scoped/singleton containers), wait strategies (waiting for a
container to actually be ready, not just started), and the CI-runner
resource and Docker-availability considerations that most commonly break
a Testcontainers suite that works fine on a developer's laptop.

## When to use

- Writing an integration test against a real database, message broker,
  or cache instead of a mock, where the mock's fidelity to the real
  system's behavior is itself a risk (SQL dialect quirks, a broker's
  actual delivery/ordering semantics, a cache's actual eviction
  behavior).
- Replacing a shared, hand-maintained integration test database/broker
  (a source of test pollution and drift) with disposable, per-run
  containers.
- Speeding up a slow Testcontainers-based suite that starts a fresh
  container per test class/method when a shared, module-scoped
  container would be safe and much faster.
- Setting up Testcontainers to run correctly in a CI runner, especially
  one using Docker-in-Docker, a remote Docker daemon, or a
  resource-constrained shared runner.
- Diagnosing a Testcontainers test that passes locally but times out,
  hangs, or fails to pull images in CI.
- Deciding whether a given integration point is worth a real container
  versus a contract test (see
  [pact-contract-testing-configuration](../pact-contract-testing-configuration/SKILL.md))
  or a lighter-weight fake.

## Prerequisites & environment

- A Docker daemon reachable from wherever tests run — local Docker
  Desktop/Docker Engine for developer machines, and a CI runner with
  Docker available (either the runner's own Docker socket mounted in,
  or a Docker-in-Docker sidecar/service, depending on the CI platform).
- The Testcontainers library for the test language/framework (`testcontainers-java`
  with JUnit 5, `testcontainers-python`, `testcontainers-go`,
  `testcontainers-node`, or the corresponding module for the test
  framework in use) plus the specific **module** for each dependency
  (e.g. `testcontainers-java`'s `postgresql`, `kafka`, and `redis`
  modules ship pre-built wait-strategy and configuration support rather
  than requiring a hand-rolled generic container setup).
- Enough CI runner resource headroom (CPU, memory, and disk for pulled
  images) for however many containers a test run starts concurrently —
  a runner sized for the application under test alone, with no margin
  for a Postgres and a Kafka broker running alongside it, is a common
  source of CI-only flakiness.
- Network/registry access from the CI runner to pull the container
  images used (a public registry, or an internal mirror/proxy if the
  organization restricts direct public registry pulls) — an air-gapped
  or heavily firewalled runner needs images pre-pulled or mirrored
  before Testcontainers can start anything.
- Testcontainers' own **Ryuk** reaper container (started automatically
  by default) requires the Docker socket to be reachable with
  permission to start and stop containers — a locked-down CI Docker
  daemon that blocks Ryuk specifically is a common source of leaked
  containers accumulating on shared runners (see Common pitfalls).

## Step-by-step guidance

1. **Start a container scoped to the narrowest safe lifecycle** — a
   fresh container per test class (or per test module/suite) is usually
   the right default; a fresh container per individual test method is
   correct only when tests genuinely need full isolation and is
   otherwise a significant, often unnecessary, speed cost:
   ```java
   // JUnit 5 + testcontainers-java: container shared across all tests
   // in this class, started once
   @Testcontainers
   class OrderRepositoryTest {
       @Container
       static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
           .withDatabaseName("orders_test")
           .withUsername("test")
           .withPassword("test");

       @Test
       void savesAndLoadsAnOrder() {
           // each test runs against the same container; state resets via
           // a transaction rollback or a schema-reset step (see step 3),
           // not by restarting the container per test
       }
   }
   ```

2. **Use a module-specific wait strategy, not a fixed sleep**, so tests
   start the moment the dependency is actually ready rather than after
   an arbitrarily guessed delay:
   ```java
   KafkaContainer kafka = new KafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.6.0"))
       .waitingFor(Wait.forListeningPort());
   ```
   ```python
   # testcontainers-python: Postgres module's built-in readiness wait
   from testcontainers.postgres import PostgresContainer

   postgres = PostgresContainer("postgres:16")
   postgres.start()  # blocks until the container reports ready, not a fixed sleep
   ```
   A fixed `sleep(10)` "wait strategy" is both slower than necessary on a
   fast machine and still flaky on a slow/loaded one (CI runners under
   contention are exactly where a too-short fixed sleep fails
   intermittently) — always prefer the module's built-in readiness check
   (log-line match, port-open check, or an actual health-check query)
   over a fixed delay.

3. **Reset state between tests deliberately**, rather than assuming a
   shared, class-scoped container implies test isolation for free:
   ```java
   @BeforeEach
   void resetSchema() {
       jdbcTemplate.execute("TRUNCATE orders, order_items RESTART IDENTITY CASCADE");
   }
   ```
   Whether reset happens via a transaction rolled back after each test,
   a `TRUNCATE`/schema-reset step, or a fresh logical database/topic per
   test is a deliberate design decision — the wrong assumption here
   (that a shared container automatically means shared, leaking state
   across tests) is the most common cause of order-dependent test
   flakiness in a Testcontainers suite.

4. **Wire the container's dynamically assigned port into the
   application/config under test**, never a hardcoded port — Testcontainers
   maps container ports to a random free host port by default
   specifically to allow parallel test runs without collisions:
   ```java
   @DynamicPropertySource
   static void registerPgProperties(DynamicPropertyRegistry registry) {
       registry.add("spring.datasource.url", postgres::getJdbcUrl);
       registry.add("spring.datasource.username", postgres::getUsername);
       registry.add("spring.datasource.password", postgres::getPassword);
   }
   ```
   ```python
   engine = create_engine(postgres.get_connection_url())
   ```
   A hardcoded port (e.g. always mapping to host port `5432`) breaks
   parallel test execution the moment two test runs (two CI jobs, two
   developers) try to bind the same host port simultaneously.

5. **Use a singleton/shared container pattern across test classes**
   when many test classes need the same dependency and per-class startup
   cost dominates suite runtime — start the container once, in a static
   initializer with no explicit `stop()`, and let Testcontainers' Ryuk
   reaper clean it up when the JVM/test process exits:
   ```java
   public abstract class AbstractIntegrationTest {
       static final PostgreSQLContainer<?> postgres =
           new PostgreSQLContainer<>("postgres:16").withReuse(true);

       static {
           postgres.start(); // started once, deliberately never stopped here
       }
   }
   ```
   `withReuse(true)` (paired with
   `testcontainers.reuse.enable=true` in `~/.testcontainers.properties`)
   goes further, keeping the same container running *across separate
   test-runner invocations* on a developer's machine for fast local
   iteration — this specific setting is a local developer-experience
   optimization and should not be relied on for CI correctness, since a
   CI runner is typically a fresh environment every run.

6. **Confirm the CI runner actually has Docker available and correctly
   configured** before assuming a Testcontainers suite will "just work"
   the same as on a developer laptop:
   ```yaml
   # GitHub Actions: ubuntu-latest runners include Docker by default;
   # nothing extra to configure for the common case
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - run: ./gradlew test
   ```
   ```yaml
   # GitLab CI: needs an explicit Docker-in-Docker service and TLS config
   test:
     image: eclipse-temurin:21-jdk
     services:
       - docker:24-dind
     variables:
       DOCKER_HOST: tcp://docker:2376
       DOCKER_TLS_CERTDIR: "/certs"
     script:
       - ./gradlew test
   ```
   A CI platform that doesn't provide Docker by default (or provides it
   only via an explicitly-declared Docker-in-Docker service, as GitLab
   does) is the most common reason a Testcontainers suite passes locally
   and fails outright in CI with a connection-refused error before any
   test logic even runs.

7. **Size CI runner resources for every container the suite starts
   concurrently**, not just for the application under test:
   ```yaml
   # a runner/executor resource request sized for the app plus
   # a Postgres and a Kafka broker running alongside it during tests
   resources:
     requests:
       cpu: "2"
       memory: "4Gi"
   ```
   A runner sized only for running the application's own test process
   commonly OOMs or throttles severely once a real Postgres and a real
   Kafka broker are also competing for the same constrained CPU/memory —
   size explicitly for the concurrent container load, not just the test
   process.

8. **Pin exact image tags for every container module**, not `latest` —
   an unpinned image tag means a suite's behavior (and its exact
   startup time/readiness signal) can shift under a test run with no
   corresponding code change:
   ```java
   new PostgreSQLContainer<>("postgres:16.4") // pinned, not "postgres:latest"
   ```

9. **Prefer the language ecosystem's native Testcontainers module over a
   generic container definition** where one exists — the Postgres/
   Kafka/Redis-specific modules ship pre-tuned wait strategies and
   convenience accessors (`getJdbcUrl()`, `getBootstrapServers()`) that
   a hand-rolled `GenericContainer` setup has to reimplement and is more
   likely to get subtly wrong:
   ```java
   // prefer this
   new PostgreSQLContainer<>("postgres:16.4");
   // over hand-rolling the equivalent with GenericContainer, unless no
   // maintained module exists for the target dependency
   ```

## Best practices

- Default to a class/module-scoped shared container over a fresh
  container per test method — reserve per-test containers for cases
  that genuinely need full isolation, since container startup cost adds
  up fast across a large suite.
- Reset data state explicitly between tests (truncate, transaction
  rollback, or a fresh logical namespace) rather than assuming a shared
  container implies automatic test isolation.
- Always use the module's built-in wait strategy over a fixed sleep —
  this is both faster on capable hardware and more reliable on
  contended/slow CI runners.
- Never hardcode a container's host port — read it dynamically from the
  Testcontainers API so tests can run in parallel without port
  collisions.
- Pin exact image tags for every container used in tests, the same
  version-discipline applied to any other dependency.
- Confirm Docker availability and resource sizing in CI explicitly
  before assuming a suite that works locally will behave identically —
  this is the single most common source of "works on my machine, fails
  in CI" for Testcontainers-based suites.
- Reserve `withReuse(true)` for local developer-experience speedups, not
  as a correctness assumption in CI, where runners are typically fresh
  per run anyway.

## Common pitfalls

- **Symptom:** A Testcontainers suite passes reliably on every
  developer's laptop and fails immediately in CI with a connection-
  refused or "cannot connect to the Docker daemon" error.
  **Fix:** The CI runner either has no Docker daemon available at all,
  or (on platforms like GitLab CI) needs an explicit Docker-in-Docker
  service declared and `DOCKER_HOST` configured (step 6) — this isn't a
  test-code bug, it's a CI environment gap. Confirm Docker's actual
  availability and configuration on the specific CI platform before
  debugging the test code itself.

- **Symptom:** The same Testcontainers suite is markedly slower or
  intermittently times out only when run in CI, not locally.
  **Fix:** The CI runner is under-resourced for however many containers
  the suite starts concurrently (step 7) — a shared/constrained CI
  executor competing for CPU/memory across a real Postgres, a real
  Kafka broker, and the application's own test process is a common,
  easy-to-miss capacity gap. Size the runner's resource requests/limits
  explicitly for the concurrent container load, not just the
  application process.

- **Symptom:** Tests pass individually but fail intermittently when run
  as a full suite, especially in a particular order.
  **Fix:** State from one test leaks into the next because the shared,
  class-scoped container's data was never reset between tests (step 3)
  — a common mistaken assumption that a shared container implies shared
  test isolation for free. Add an explicit reset step (truncate,
  transaction rollback, fresh topic/namespace per test) between tests.

- **Symptom:** Two parallel CI jobs (or two developers running tests
  locally at the same time) both fail with a port-already-in-use error.
  **Fix:** A container port was hardcoded instead of read dynamically
  from the Testcontainers API (step 4) — Testcontainers maps to a random
  free host port specifically to avoid this; hardcoding a fixed port
  defeats that and breaks any parallel execution.

- **Symptom:** Over weeks, a shared CI runner (or a developer's local
  Docker daemon) accumulates dozens of leftover, no-longer-needed
  containers from past test runs.
  **Fix:** Testcontainers' Ryuk reaper (which cleans up containers after
  the test process exits) either couldn't reach the Docker socket due to
  a restrictive daemon/network policy, or was explicitly disabled
  (`TESTCONTAINERS_RYUK_DISABLED=true`) without a replacement cleanup
  mechanism. Confirm Ryuk can actually run in the target environment,
  and if it genuinely must be disabled (some locked-down CI/security
  policies block it), add an explicit scheduled cleanup step instead of
  leaving orphaned containers to accumulate silently.

## Worked example

**Scenario:** `order-service`'s repository layer is tested against a
real Postgres instead of a mocked JDBC driver, and its Kafka event
publisher is tested against a real Kafka broker instead of a mocked
producer — both need to run reliably in GitHub Actions CI, in parallel
across multiple test suites.

```java
public abstract class AbstractIntegrationTest {
    static final PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16.4")
            .withDatabaseName("orders_test")
            .withUsername("test")
            .withPassword("test");

    static final KafkaContainer kafka =
        new KafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.6.0"));

    static {
        postgres.start();
        kafka.start();
    }

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
    }
}

class OrderRepositoryIntegrationTest extends AbstractIntegrationTest {
    @BeforeEach
    void resetSchema() {
        jdbcTemplate.execute("TRUNCATE orders RESTART IDENTITY CASCADE");
    }

    @Test
    void persistsAndReloadsAnOrder() {
        Order saved = orderRepository.save(new Order("ORD-1", 4999));
        assertThat(orderRepository.findById(saved.getId()).getAmountCents()).isEqualTo(4999);
    }
}

class OrderEventPublisherIntegrationTest extends AbstractIntegrationTest {
    @Test
    void publishesOrderCreatedEvent() throws Exception {
        orderEventPublisher.publish(new OrderCreatedEvent("ORD-2", 1999));
        ConsumerRecords<String, String> records = testConsumer.poll(Duration.ofSeconds(5));
        assertThat(records).hasSize(1);
    }
}
```

CI (GitHub Actions, Docker available by default on `ubuntu-latest`, no
extra Docker-in-Docker configuration needed):
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { java-version: '21', distribution: 'temurin' }
      - run: ./gradlew test
```

Both `postgres` and `kafka` are started once as static fields shared
across both test classes (extending the same `AbstractIntegrationTest`),
keeping suite startup cost to one Postgres and one Kafka container
total rather than one pair per test class; `TRUNCATE` before each
repository test keeps state isolated without restarting the container.

## Cross-references

- [pact-contract-testing-configuration](../pact-contract-testing-configuration/SKILL.md) — a complementary integration-testing approach: contract tests verify the *shape* of an interaction between independently-deployed services without needing either side's real dependency running, while Testcontainers verifies real behavior against an actual dependency instance within one service's own test suite — many systems benefit from both, applied to different kinds of integration risk.
- [infrastructure-post-deployment-validation-and-smoke-testing](../infrastructure-post-deployment-validation-and-smoke-testing/SKILL.md) — the post-deploy validation layer that picks up once code has already passed the Testcontainers-backed integration tests covered here.
- [makefile-authoring-and-validation](../makefile-authoring-and-validation/SKILL.md) — a common place to wrap the Docker-availability and resource-sizing preconditions this skill's CI guidance depends on into a single reusable local/CI entry point.
