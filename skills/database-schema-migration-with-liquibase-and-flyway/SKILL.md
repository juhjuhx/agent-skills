---
name: database-schema-migration-with-liquibase-and-flyway
description: >
  Covers version-controlled schema migration tooling (Liquibase
  changesets/changelogs, Flyway versioned/repeatable migrations),
  forward-only vs. reversible migration design, safe patterns for
  backward-compatible rolling deploys, and testing migrations in CI
  before they reach production. Use when the user asks to "set up
  Flyway/Liquibase for this project," "write a rollback for this
  migration," "why did this migration fail halfway through," "how do I
  test a schema migration in CI," or "design a zero-downtime column
  rename/backfill."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: database-operations
  maturity: stable
---

# Database Schema Migration with Liquibase and Flyway

## Purpose

Schema migrations are the one place where "it worked in my local
database" and "it's safe to run against production" are routinely two
very different claims — a migration that runs cleanly against an empty
or small test database can lock a large production table for minutes,
and a migration applied without considering the currently-running
(old-version) application code can break it mid-rollout. This skill
covers the two dominant version-controlled migration tools —
**Liquibase** (XML/YAML/SQL changesets tracked in a changelog, with
built-in rollback support) and **Flyway** (plain versioned SQL/Java
migrations, forward-only by convention) — the forward-only-vs-
reversible design decision itself, backward-compatible migration
patterns for zero-downtime rolling deploys, and testing migrations in
CI before they ever reach a real environment. It complements the
database-specific operational skills in this repo
([postgresql-operations-and-performance-tuning](../postgresql-operations-and-performance-tuning/SKILL.md),
[mongodb-operations-and-scaling](../mongodb-operations-and-scaling/SKILL.md))
by covering the tooling and process layer that should sit in front of
any hand-run DDL change against those systems.

## When to use

- Introducing version-controlled migration tooling (Liquibase or
  Flyway) to a project that currently applies schema changes by hand or
  via untracked scripts.
- Writing a new migration and deciding whether it needs (or can have) a
  rollback, and if forward-only, what the recovery plan is instead.
- A migration failed partway through and left the schema (and the
  tool's tracking table) in an inconsistent state.
- Designing a schema change (column rename, type change, NOT NULL
  addition, table split) that must not break the currently-running
  application during a rolling deploy where old and new code run
  simultaneously.
- Setting up CI to actually run migrations against a real (or realistic)
  database before merge, rather than only reviewing the SQL by eye.
- Migrating from one tool to another, or reconciling a migration
  history that's drifted from actual schema state.

## Prerequisites & environment

- A migration tool already chosen or being evaluated: Liquibase 4.x
  or Flyway 9.x/10.x assumed for the syntax below — note explicitly
  where community vs. paid-tier features differ (Flyway's undo
  migrations, for instance, are a paid-tier feature in current Flyway
  versions; Liquibase's rollback support is available in the open-
  source edition).
- A dedicated migration-tracking table the tool manages itself
  (`DATABASECHANGELOG`/`DATABASECHANGELOGLOCK` for Liquibase,
  `flyway_schema_history` for Flyway) — never manually edit these
  tables except as a deliberate, understood recovery action (step 5
  below), since the tool trusts them as the source of truth for what's
  already been applied.
- A CI pipeline capable of spinning up a real instance of the target
  database engine (a container is the common approach) to run
  migrations against, not just a linter/syntax check — schema migration
  correctness (does it apply cleanly, does it produce the expected
  resulting schema) can't be fully validated by reading SQL alone.
- For zero-downtime rolling-deploy patterns: an understanding of the
  actual deployment model (rolling/canary vs. all-at-once) since the
  backward-compatibility guidance in step 4 only matters if old and new
  application code genuinely run concurrently against the same schema
  at some point.
- Database credentials/roles scoped to apply DDL restricted to the CI/
  deployment pipeline's service account, not broadly available
  developer credentials, for any migration targeting a shared or
  production environment.

## Step-by-step guidance

### 1. Choose forward-only or reversible migrations deliberately, per project — not by tool default

**Flyway** is forward-only by convention in its open-source form: each
versioned migration (`V1__create_users_table.sql`) is applied once, in
order, and there is no built-in automatic rollback — "undoing" a
migration means writing and applying a *new* forward migration that
reverses the change:
```sql
-- V1__create_users_table.sql
CREATE TABLE users (id BIGINT PRIMARY KEY, email VARCHAR(255) NOT NULL);

-- V2__add_users_status_column.sql
ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active';
```
**Liquibase** supports an explicit `rollback` block per changeset,
either auto-generated for simple, reversible operations or hand-written
for anything the tool can't infer:
```xml
<changeSet id="2" author="team">
  <addColumn tableName="users">
    <column name="status" type="VARCHAR(20)" defaultValue="active">
      <constraints nullable="false"/>
    </column>
  </addColumn>
  <rollback>
    <dropColumn tableName="users" columnName="status"/>
  </rollback>
</changeSet>
```
Neither approach is universally "safer" — a Liquibase rollback for a
*destructive* forward migration (e.g. dropping a column) can only
recreate the column's structure, never the data that was in it, so a
rollback that looks complete can still be a data-loss operation in
practice. Decide per migration, not per tool: reversible changesets are
valuable for additive, low-risk changes (add a column, add an index);
purely destructive changes (drop a column/table) should be treated as
forward-only regardless of tooling, with a tested restore-from-backup
plan as the actual rollback path, not a generated `rollback` block that
can't bring data back.

### 2. Structure migrations to apply in strict, append-only order

```
migrations/
├── V1__create_users_table.sql
├── V2__add_users_status_column.sql
└── V3__create_orders_table.sql
```
Both tools enforce ordering and checksum the applied migration's
content against what's recorded in the tracking table — **never edit an
already-applied migration file** after it's run anywhere shared (CI,
staging, production); both tools will detect the checksum mismatch and
refuse to proceed (a deliberate safety feature, not a bug to work
around by disabling checksum validation). If a migration needs
correcting after being applied somewhere, write a new migration that
fixes it forward, rather than editing history.

### 3. Test every migration in CI against a real database instance, not just a syntax check

```yaml
# Example CI step (tool-neutral outline)
- name: Start test database
  run: docker run -d --name pg-test -e POSTGRES_PASSWORD=<TEST_DB_PASSWORD> -p 5432:5432 postgres:16

- name: Apply migrations from clean state
  run: flyway -url=jdbc:postgresql://localhost:5432/testdb -user=postgres migrate

- name: Verify resulting schema matches expectation
  run: psql -h localhost -U postgres -d testdb -c "\d+ users"
```
Validate three things in CI, not just "the migration ran without an
error":
- **Applies cleanly from a fresh/empty schema** — catches a migration
  that accidentally depends on manual setup someone did once and forgot
  to capture.
- **Applies cleanly on top of the current production-equivalent schema
  state** (i.e. run the full migration history in order, not just the
  new migration in isolation) — catches an ordering assumption that
  happens to work locally but conflicts with a migration merged by
  someone else in the meantime.
- **Produces the expected resulting schema** — an automated check
  (schema diff, or explicit assertions like the `\d+` example above)
  rather than only "no error was thrown," since a migration can succeed
  while producing a subtly wrong result (wrong column type, missing
  constraint).

For any migration expected to run against a large production table,
also validate its actual lock behavior and estimated duration against a
production-sized (or realistically scaled) copy in a staging
environment — CI catching a syntax/logic problem doesn't tell you a
migration will lock a 200M-row table for ten minutes in production.

### 4. Design backward-compatible migrations for rolling deploys — expand/contract, not a single atomic swap

When old and new application code run simultaneously during a rolling
deploy, a single migration that both changes the schema and requires
the new code's expectations to already hold will break the still-
running old code. Use the **expand/contract** pattern across multiple
deploys instead of one atomic change:

For a column rename (`email` → `email_address`):
1. **Expand** (migration N, deploy N): add the new column, backfill it,
   keep both columns and keep old code writing to the old column (or
   dual-write to both from new code):
   ```sql
   ALTER TABLE users ADD COLUMN email_address VARCHAR(255);
   UPDATE users SET email_address = email WHERE email_address IS NULL;
   ```
2. **Migrate application code** (deploy N+1): new code reads/writes
   `email_address`; deploy and confirm fully rolled out (no old-code
   instances remain writing only to `email`).
3. **Contract** (migration N+2, deploy N+2, once N+1 is fully rolled
   out and stable): drop the old column.
   ```sql
   ALTER TABLE users DROP COLUMN email;
   ```
This spreads a single "rename" across three coordinated, individually
safe steps instead of one migration that breaks whichever code version
isn't expecting it. The same pattern applies to adding a `NOT NULL`
constraint (add nullable, backfill, then add the constraint in a
later migration once backfill is confirmed complete) and to type
changes (add new-typed column, dual-write/backfill, cut reads over,
drop old column).

### 5. Recover deliberately from a migration that failed partway through

A migration that fails mid-execution (e.g. a DDL statement inside a
multi-statement migration succeeds but a later statement in the same
file fails) can leave the tracking table and actual schema
inconsistent — Flyway marks the migration as failed
(`flyway_schema_history` shows `success = false`) and refuses to apply
further migrations until resolved; Liquibase similarly halts and may
leave a stale lock row in `DATABASECHANGELOGLOCK`.
```bash
# Flyway: after manually confirming/fixing the actual schema state,
# either repair the checksum/history or explicitly mark resolved
flyway repair
```
```sql
-- Liquibase: after confirming no other process is actually running a
-- migration, clear a stale lock
UPDATE DATABASECHANGELOGLOCK SET LOCKED = FALSE, LOCKGRANTED = NULL, LOCKEDBY = NULL WHERE ID = 1;
```
> **Warning — proceed carefully.** `flyway repair` and manually clearing
> a Liquibase lock both tell the tool to trust a new claim about
> reality rather than re-verifying it — only do this after manually
> confirming the actual current schema state matches what you're about
> to tell the tool it is (e.g. did that failed `ALTER TABLE` actually
> apply partially, or not at all, on this specific database engine's
> DDL transactionality model). Clearing a lock or repairing history
> against a schema state that doesn't match will cause the *next*
> migration to apply against the wrong assumed baseline, potentially
> silently.

Note that DDL transactionality differs by engine: PostgreSQL wraps most
DDL in a transaction that rolls back cleanly on failure (so a failed
migration often leaves the schema exactly as it was before), while
MySQL's DDL is largely non-transactional (each statement commits
immediately, so a multi-statement migration that fails partway through
can leave a genuinely mixed schema state) — validate which applies to
your engine before assuming a failed migration left no partial effect.

## Best practices

- Decide reversibility per migration based on whether the underlying
  operation is genuinely reversible (additive changes) or destructive
  (drops), not by defaulting to "always write a rollback" or "never
  write one" fleet-wide — a generated rollback for a destructive change
  is false confidence, not a real safety net.
- Never edit an already-applied migration file; fix forward with a new
  migration instead, and let the tool's checksum validation catch
  attempts to do otherwise rather than disabling that check to "make CI
  green."
- Run the full migration history against a fresh schema in CI on every
  change, not just the newest migration in isolation, to catch ordering
  conflicts from concurrent work.
- Use the expand/contract pattern for any schema change that isn't
  purely additive, whenever the deployment model involves old and new
  application code running concurrently even briefly.
- Validate lock duration and estimated runtime for any migration
  targeting a large, actively-written production table against a
  realistically-sized staging copy — a migration tested only against a
  near-empty CI database gives no signal about production lock impact.
- Restrict the credentials that can apply migrations against shared/
  production environments to the CI/deployment pipeline's own service
  account, not general developer credentials, so ad hoc manual DDL
  changes can't drift out of the tracked migration history.

## Common pitfalls

- **Symptom:** A migration that ran fine in CI and staging locks a
  production table for several minutes, causing request timeouts.
  **Fix:** CI/staging validated correctness against a small dataset but
  not lock behavior against production-scale data. Some DDL operations
  (adding a column with a non-null default on older engine versions,
  building an index without a concurrent/online option, adding a
  foreign key constraint that must scan and validate the whole table)
  scale their lock duration with table size, not just row-by-row
  complexity. Validate long-running DDL against a production-sized
  staging copy, and prefer online/concurrent variants (e.g.
  `CREATE INDEX CONCURRENTLY` in PostgreSQL) where the engine
  and migration tool both support expressing that in the migration.

- **Symptom:** A "rollback" of a migration that dropped a column
  restores the column's structure, but all the data that used to be in
  it is gone.
  **Fix:** A generated or hand-written rollback for a destructive
  operation can only reconstruct schema shape, never the deleted data.
  Treat any migration that drops a column/table as forward-only in
  practice, with a tested restore-from-backup (or a preceding backup
  step in the deployment process) as the real recovery path, and don't
  let a syntactically-valid `rollback` block create false confidence
  that it's a genuine undo.

- **Symptom:** During a rolling deploy, some requests fail with a
  "column does not exist" (or the reverse — an unexpected NOT NULL
  violation) error for several minutes, then it resolves on its own.
  **Fix:** A single migration changed the schema in a way that broke
  whichever application code version (old or new) wasn't expecting it,
  while both versions were running concurrently during the rollout.
  Redesign the change using expand/contract across multiple deploys
  (add-and-backfill, migrate code, then remove-old) instead of one
  atomic schema change coupled to a simultaneous code deploy.

- **Symptom:** A migration fails partway through in CI or staging, and
  after someone manually fixes the schema and clears the tool's lock/
  failed-state, the *next* migration then fails or produces an
  unexpected schema.
  **Fix:** The manual fix didn't actually bring the schema to the exact
  state the tool was told to trust (e.g. `flyway repair` was run
  without first confirming exactly which statements in the failed
  migration had actually applied). Before repairing/clearing a failed-
  migration state, explicitly diff the actual current schema against
  what the migration was supposed to produce, and only then tell the
  tool to trust that state.

- **Symptom:** Someone manually runs an ad hoc `ALTER TABLE`/`DROP
  COLUMN` directly against production "to fix something quickly,"
  bypassing the migration tool entirely, and it isn't tracked anywhere.
  **Fix:** This is a destructive/high-risk action if run without a
  rollback plan, and it also desynchronizes the tracked migration
  history from actual schema reality — the next real migration run may
  assume a baseline that's no longer accurate. Restrict DDL privileges
  on shared/production databases to the migration pipeline's service
  account so ad hoc manual changes aren't possible, and if an emergency
  manual change is unavoidable, immediately codify it as a proper
  migration (even if the tool then just no-ops because it was already
  applied) so the tracked history stays the source of truth.

## Worked example

**Scenario:** A `users` table needs its `email` column renamed to
`email_address`, and the service deploys via a rolling strategy where
old and new application pods run simultaneously for several minutes
during rollout. The team uses Flyway.

1. **Expand** — migration `V12`, deployed alongside application code
   that dual-writes to both columns but still reads from `email`:
   ```sql
   -- V12__add_email_address_column.sql
   ALTER TABLE users ADD COLUMN email_address VARCHAR(255);
   UPDATE users SET email_address = email WHERE email_address IS NULL;
   ```
   CI validates this applies cleanly against both a fresh schema and
   the current full migration history, and a staging run against a
   production-sized copy confirms the backfill `UPDATE` completes in an
   acceptable window (batched if the table were large enough to need
   it — not needed here at this table's actual size).
2. **Migrate application code** — deploy N+1 changes the application to
   read from `email_address` (still dual-writing to `email` for
   safety during this rollout) and confirm via deployment tooling that
   100% of running instances are on the new version before proceeding.
3. **Stop dual-write** — deploy N+2 removes the write to the old
   `email` column now that all instances read/write `email_address`
   only, confirmed fully rolled out.
4. **Contract** — migration `V13`, once N+2 has been stable for an
   agreed bake period with no rollback needed:
   ```sql
   -- V13__drop_email_column.sql
   ALTER TABLE users DROP COLUMN email;
   ```
   This migration is treated as forward-only and destructive — the team
   confirms a recent verified backup exists before applying it to
   production, rather than relying on any generated rollback to restore
   dropped data if something is later found to still depend on the old
   column.
5. Each migration is tested in CI against both a fresh schema and the
   full accumulated history before merge, so a colleague's
   concurrently-merged migration touching the same table would have
   surfaced an ordering conflict before reaching staging.

## Cross-references

- [postgresql-operations-and-performance-tuning](../postgresql-operations-and-performance-tuning/SKILL.md) — the underlying PostgreSQL mechanics (`CREATE INDEX CONCURRENTLY`, lock behavior, vacuum impact of large `UPDATE`/backfill statements) that a migration's DDL should be validated against for lock/performance safety.
- [postgresql-high-availability-and-failover](../postgresql-high-availability-and-failover/SKILL.md) — migrations must target the current Patroni-elected primary through the same connection-routing layer as application traffic, not a specific node hostname, to avoid applying DDL to the wrong node during a failover window.
- [mongodb-operations-and-scaling](../mongodb-operations-and-scaling/SKILL.md) — MongoDB is schemaless, but index and shard-key changes there deserve the same tracked, reviewed, forward-planned change process described here rather than ad hoc shell commands.
