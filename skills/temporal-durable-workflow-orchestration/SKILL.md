---
name: temporal-durable-workflow-orchestration
description: >
  Guides authoring Temporal workflows and activities using the durable
  execution model — deterministic workflow code that automatically
  replays from event history after a crash, activities that retry
  independently with their own backoff policy, and signals/queries for
  interacting with a long-running workflow from the outside. Use when the
  user asks to "write a Temporal workflow," "model a saga/multi-step
  business process with Temporal," "add a signal to a running workflow,"
  "design activity retry policies," or is choosing Temporal over
  Airflow/Dagster for a long-running, stateful *application* workflow
  (e.g. an order fulfillment saga) rather than a scheduled batch data
  pipeline.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: messaging-and-data-orchestration
  maturity: stable
---

# Temporal Durable Workflow Orchestration

## Purpose

Temporal implements **durable execution**: a workflow's code runs as
normal function/method logic, but every meaningful event (an activity
completing, a timer firing, a signal arriving) is appended to a
persisted **event history** on the Temporal server, and the workflow's
state is reconstructed by **replaying** that history against the same
code whenever a worker picks the workflow back up — after a worker
crash, a deploy, or a deliberate worker restart. This makes a workflow
that runs for minutes, days, or months as durable as a single
transaction, with no external database, message queue, or scheduler of
its own to build and operate. This is a fundamentally different tool
than [airflow-dag-authoring-and-validation](../airflow-dag-authoring-and-validation/SKILL.md)
or [dagster-and-prefect-pipeline-authoring](../dagster-and-prefect-pipeline-authoring/SKILL.md):
those orchestrate *batch data pipelines* on a schedule, where a "task"
is typically a bounded unit of data processing and the unit of state is
a DAG run for a given logical date. Temporal orchestrates **long-running,
stateful application logic** — a multi-step saga like order fulfillment,
a user onboarding flow waiting days for a human action, or a
distributed-transaction-style process coordinating several services —
where the unit of state is the workflow's own execution history and
external actors interact with a *specific, addressable, still-running
instance* via signals and queries, not a scheduled trigger. This skill
covers authoring that workflow/activity/signal model correctly;
validating worker, timeout, retry, and namespace configuration before
production is covered separately in
[temporal-configuration-validation](../temporal-configuration-validation/SKILL.md).

## When to use

- Modeling a multi-step business process that must survive a crash,
  deploy, or long wait between steps — an order fulfillment saga, a
  loan-approval flow waiting on a human, a multi-day trial-to-paid
  conversion sequence.
- Coordinating calls across several services where a partial failure
  needs an explicit compensating action (a saga pattern), rather than
  hoping a single distributed transaction holds.
- Adding a **signal** so an external event (a human approval, a webhook,
  a cancellation request) can affect an already-running workflow
  instance.
- Adding a **query** so an external caller can read a running workflow's
  current state without affecting its execution.
- Deciding whether a given process belongs in Temporal versus a
  scheduled batch pipeline (Airflow/Dagster) — see the Purpose section's
  distinction before defaulting to whichever tool the team already
  knows.
- Reviewing existing workflow code for non-determinism that would break
  replay (the single most common Temporal authoring mistake).

## Prerequisites & environment

- A running **Temporal Server** (Temporal Cloud, or self-hosted via
  `docker compose` / the `temporal` Helm chart) reachable from worker
  processes — self-hosted deployments also need a supported persistence
  store (PostgreSQL, MySQL, or Cassandra) and, for production, Elasticsearch
  or OpenSearch if visibility/advanced search (`temporal workflow list`
  filters) is required.
- A Temporal SDK matching the language the workflow/activity code is
  written in (Go, Java, TypeScript/Node.js, Python, .NET, PHP) — this
  skill's examples use the Go and TypeScript SDKs, but the
  workflow/activity/signal concepts are identical across all of them.
- At least one **worker** process running and polling a specific **task
  queue** — workflows and activities do not execute anywhere until a
  worker is actively polling the task queue they were started/scheduled
  on; an idle-looking workflow is very often just waiting for a worker
  that was never started or crashed and wasn't restarted.
- A **namespace** created on the server (`temporal operator namespace
  create`) to isolate this workflow's task queues, workflow IDs, and
  retention policy from other applications sharing the same cluster.
- Familiarity with the determinism constraint (step 1) before writing
  any workflow code — this is the one prerequisite that, if skipped,
  produces workflows that pass every test locally and then fail
  non-deterministically in production after the first worker restart.

## Step-by-step guidance

1. **Write workflow code as deterministic orchestration logic only** —
   no direct network calls, no raw `time.Now()`/`Date.now()`, no
   unseeded randomness, no reading environment variables or local
   filesystem state directly inside the workflow function. All of that
   belongs in an **activity**, which the workflow calls and awaits:
   ```go
   // Go SDK — workflow function: pure orchestration, no side effects directly
   func OrderFulfillmentWorkflow(ctx workflow.Context, order Order) error {
       ao := workflow.ActivityOptions{
           StartToCloseTimeout: 30 * time.Second,
           RetryPolicy: &temporal.RetryPolicy{
               InitialInterval:    time.Second,
               BackoffCoefficient: 2.0,
               MaximumInterval:    time.Minute,
               MaximumAttempts:    5,
           },
       }
       ctx = workflow.WithActivityOptions(ctx, ao)

       var reservation ReservationResult
       if err := workflow.ExecuteActivity(ctx, ReserveInventory, order).Get(ctx, &reservation); err != nil {
           return err
       }
       var charge ChargeResult
       if err := workflow.ExecuteActivity(ctx, ChargePayment, order).Get(ctx, &charge); err != nil {
           // compensate: release the inventory already reserved
           _ = workflow.ExecuteActivity(ctx, ReleaseInventory, reservation).Get(ctx, nil)
           return err
       }
       return workflow.ExecuteActivity(ctx, ShipOrder, order).Get(ctx, nil)
   }
   ```
   The workflow function itself never talks to a payment gateway or an
   inventory database directly — `ReserveInventory`, `ChargePayment`,
   `ReleaseInventory`, and `ShipOrder` are activities that perform the
   actual I/O and can fail/retry independently of the workflow's own
   deterministic control flow.

2. **Write activities as ordinary, non-deterministic code with real side
   effects** — an activity is where network calls, database writes, and
   third-party API calls belong, and each activity gets its own timeout
   and retry policy scoped to what that specific call actually needs:
   ```go
   func ChargePayment(ctx context.Context, order Order) (ChargeResult, error) {
       resp, err := paymentClient.Charge(ctx, order.CustomerID, order.TotalCents)
       if err != nil {
           return ChargeResult{}, fmt.Errorf("charge failed: %w", err)
       }
       return ChargeResult{ChargeID: resp.ID}, nil
   }
   ```
   An activity that legitimately runs longer than its `StartToCloseTimeout`
   should call `activity.RecordHeartbeat(ctx, progress)` periodically so
   Temporal knows it's still alive rather than assuming it's stuck —
   pair a heartbeat with a `HeartbeatTimeout` shorter than
   `StartToCloseTimeout` so a genuinely hung activity is detected and
   retried promptly instead of waiting out the full timeout.

3. **Scope retry policies to each activity's actual failure mode**, not
   one blanket policy copy-pasted everywhere — a payment charge that
   might legitimately need a human to look at it after a few attempts
   should not retry the same way a transient network blip to an internal
   inventory service should:
   ```go
   chargeOptions := workflow.ActivityOptions{
       StartToCloseTimeout: 15 * time.Second,
       RetryPolicy: &temporal.RetryPolicy{
           InitialInterval:        time.Second,
           BackoffCoefficient:     2.0,
           MaximumInterval:        30 * time.Second,
           MaximumAttempts:        3,
           NonRetryableErrorTypes: []string{"CardDeclinedError"},
       },
   }
   ```
   `NonRetryableErrorTypes` stops Temporal from burning through retries on
   an error that will never succeed by trying again (a declined card is
   a business outcome to handle in the workflow, not a transient fault to
   retry past).

4. **Use signals for external events that affect a running workflow**,
   and design the workflow to wait on them with `workflow.Await` (or the
   SDK's equivalent selector/channel pattern) rather than polling:
   ```go
   func OrderFulfillmentWorkflow(ctx workflow.Context, order Order) error {
       var approved bool
       approvalChan := workflow.GetSignalChannel(ctx, "manager-approval")

       selector := workflow.NewSelector(ctx)
       selector.AddReceive(approvalChan, func(c workflow.ReceiveChannel, more bool) {
           c.Receive(ctx, &approved)
       })
       selector.Select(ctx) // blocks until the signal arrives, no polling

       if !approved {
           return workflow.NewApplicationError("order rejected by manager", "OrderRejected")
       }
       // ... continue fulfillment
       return nil
   }
   ```
   A caller sends the signal against the workflow's specific, addressable
   `WorkflowID` — this is the mechanism that lets an external human
   action ("approve this order") reach one specific in-flight workflow
   instance among potentially millions.

5. **Use queries for read-only introspection of a running workflow's
   state**, never to trigger a side effect — a query handler must not
   mutate workflow state or call activities:
   ```go
   func OrderFulfillmentWorkflow(ctx workflow.Context, order Order) error {
       status := "pending"
       err := workflow.SetQueryHandler(ctx, "getStatus", func() (string, error) {
           return status, nil
       })
       if err != nil {
           return err
       }
       // ... status is updated ("reserved", "charged", "shipped") as
       // the workflow progresses through activities
       return nil
   }
   ```

6. **Bound unbounded event history with `Continue-As-New`** for
   workflows that loop indefinitely or process very large numbers of
   events over their lifetime — Temporal's event history for a single
   workflow execution has practical size and item-count limits, and a
   workflow that never completes will eventually hit them:
   ```go
   func PollingWorkflow(ctx workflow.Context, state State) error {
       for i := 0; i < 1000; i++ {
           // ... do bounded work per iteration
       }
       // hand off to a new execution with a fresh, empty history,
       // carrying forward only the state that needs to persist
       return workflow.NewContinueAsNewError(ctx, PollingWorkflow, state)
   }
   ```

7. **Version workflow code changes safely** using `workflow.GetVersion`
   (or the SDK's patching API) rather than editing existing workflow code
   in place — an in-flight workflow execution replays against whatever
   code is currently deployed, and a code change that alters the sequence
   of decisions a still-running workflow already took breaks replay for
   every workflow instance still executing the old logic:
   ```go
   v := workflow.GetVersion(ctx, "add-fraud-check", workflow.DefaultVersion, 1)
   if v == workflow.DefaultVersion {
       // old path: existing in-flight executions replay this branch
   } else {
       // new path: only new workflow executions (and old ones that
       // haven't reached this point yet) take this branch
       if err := workflow.ExecuteActivity(ctx, RunFraudCheck, order).Get(ctx, nil); err != nil {
           return err
       }
   }
   ```

8. **Set an explicit, meaningful `WorkflowID`**, derived from a real
   business key (an order ID, a user ID plus process type) rather than
   a random UUID — this is what makes a workflow addressable for
   signals/queries and gives Temporal's ID-reuse policy something
   sensible to enforce (e.g. rejecting a second concurrent
   `order-fulfillment-<order_id>` workflow for the same order):
   ```go
   workflowOptions := client.StartWorkflowOptions{
       ID:        fmt.Sprintf("order-fulfillment-%s", order.ID),
       TaskQueue: "order-fulfillment-tq",
   }
   ```

## Best practices

- Keep all I/O, randomness, and wall-clock time reads inside activities
  — the workflow function itself should be a pure, replayable
  orchestration of activity calls, timers, and signal/query handling.
- Design compensating activities (undo actions) alongside the "forward"
  activities for any saga-style workflow, and call them explicitly on
  failure — Temporal does not roll back completed activities
  automatically; compensation is application logic the workflow author
  writes.
- Scope each activity's timeout and retry policy to that specific call's
  real failure characteristics, and mark genuinely non-retryable errors
  (business rejections, not transient faults) as non-retryable so
  workflows fail fast on outcomes retries can never fix.
- Use `Continue-As-New` proactively for any workflow with an
  unbounded or very large loop, well before hitting history size/count
  limits, not as a reactive fix after a workflow starts failing.
- Version any change to a workflow's decision sequence with
  `GetVersion`/patching before deploying it while older executions of
  that same workflow type are still in flight.
- Choose a deterministic, business-derived `WorkflowID` and lean on
  Temporal's workflow ID reuse policy to prevent accidental duplicate
  executions for the same real-world entity.
- Treat Temporal as the tool for stateful, long-running *application*
  processes with addressable in-flight instances — keep scheduled,
  bulk, tabular batch-data processing in Airflow/Dagster rather than
  reimplementing a DAG scheduler's job inside Temporal workflows.

## Common pitfalls

- **Symptom:** A workflow runs fine in local testing, then after the
  worker is redeployed, an in-flight execution fails with a
  nondeterminism error (e.g. "unexpected activity" or "history event
  mismatch").
  **Fix:** The deployed workflow code changed the sequence of decisions
  (added/removed/reordered an activity call, changed a branch condition)
  while executions on the old code version were still in flight. Wrap
  the changed logic in `workflow.GetVersion`/the SDK's patching API
  (step 7) so old executions keep replaying their original branch and
  only new executions take the new one, rather than editing the
  decision sequence in place.

- **Symptom:** A workflow appears to "hang" indefinitely — no activities
  execute, no errors are logged anywhere.
  **Fix:** No worker is actually polling the task queue the workflow (or
  its activities) was started on — check `temporal task-queue describe
  --task-queue <queue>` for zero pollers, which is a far more common
  cause than an actual workflow bug. Confirm the worker process is
  running, healthy, and configured with the exact task queue name the
  workflow/activity options specify (a typo'd or mismatched queue name
  produces this exact silent-hang symptom).

- **Symptom:** A long-running activity is killed and retried repeatedly
  even though it's still making real progress.
  **Fix:** The activity has no `HeartbeatTimeout` configured (or one set
  shorter than how often it can realistically report progress) and isn't
  calling `RecordHeartbeat`. Add periodic heartbeating inside the
  activity and a `HeartbeatTimeout` Temporal can use to distinguish "the
  worker running this activity died" from "this activity is just slow" —
  without a heartbeat, Temporal has only `StartToCloseTimeout` to go on,
  which forces a choice between killing genuinely slow-but-healthy work
  or setting the timeout so generously that real hangs go undetected for
  a long time.

- **Symptom:** A workflow's event history grows until the workflow
  starts failing outright, or the server logs warnings about history
  size for a specific workflow.
  **Fix:** A loop (a polling workflow, a long-lived saga processing many
  discrete events) never calls `Continue-As-New` and keeps accumulating
  history indefinitely. Add a bounded iteration count or event count per
  execution and hand off to a fresh execution via
  `workflow.NewContinueAsNewError` (step 6) well before hitting the
  server's history limits.

- **Symptom:** Two workflow executions end up racing to process the same
  business entity (e.g. two `order-fulfillment` workflows both acting on
  the same order).
  **Fix:** The `WorkflowID` used at start time was a random ID rather
  than one derived from the business key, so Temporal's ID-reuse
  protections had nothing meaningful to enforce. Use a deterministic
  `WorkflowID` (step 8) tied to the real entity, and set an explicit
  `WorkflowIDReusePolicy` (e.g. reject duplicate while running) matching
  the business rule that only one in-flight fulfillment per order should
  exist.

## Worked example

**Scenario:** An `order-fulfillment` saga must reserve inventory, charge
payment, and ship an order — with a compensating inventory release if
payment fails, and a manager-approval signal required for orders over a
configured amount before shipment proceeds.

```go
func OrderFulfillmentWorkflow(ctx workflow.Context, order Order) error {
    ao := workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            InitialInterval: time.Second, BackoffCoefficient: 2.0,
            MaximumInterval: time.Minute, MaximumAttempts: 5,
        },
    }
    ctx = workflow.WithActivityOptions(ctx, ao)

    var reservation ReservationResult
    if err := workflow.ExecuteActivity(ctx, ReserveInventory, order).Get(ctx, &reservation); err != nil {
        return err
    }

    if order.TotalCents > 100000 { // over $1,000 — requires manager approval
        var approved bool
        workflow.GetSignalChannel(ctx, "manager-approval").Receive(ctx, &approved)
        if !approved {
            _ = workflow.ExecuteActivity(ctx, ReleaseInventory, reservation).Get(ctx, nil)
            return workflow.NewApplicationError("order rejected by manager", "OrderRejected")
        }
    }

    var charge ChargeResult
    chargeCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 15 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            InitialInterval: time.Second, BackoffCoefficient: 2.0,
            MaximumInterval: 30 * time.Second, MaximumAttempts: 3,
            NonRetryableErrorTypes: []string{"CardDeclinedError"},
        },
    })
    if err := workflow.ExecuteActivity(chargeCtx, ChargePayment, order).Get(ctx, &charge); err != nil {
        // compensating action: undo the inventory reservation
        _ = workflow.ExecuteActivity(ctx, ReleaseInventory, reservation).Get(ctx, nil)
        return err
    }

    return workflow.ExecuteActivity(ctx, ShipOrder, order).Get(ctx, nil)
}
```

Starting the workflow with a deterministic ID tied to the order:
```go
_, err := temporalClient.ExecuteWorkflow(context.Background(), client.StartWorkflowOptions{
    ID:                    fmt.Sprintf("order-fulfillment-%s", order.ID),
    TaskQueue:             "order-fulfillment-tq",
    WorkflowIDReusePolicy: enums.WORKFLOW_ID_REUSE_POLICY_REJECT_DUPLICATE,
}, OrderFulfillmentWorkflow, order)
```

A manager approving a large order signals the exact running instance:
```bash
temporal workflow signal \
  --workflow-id order-fulfillment-ORD-48213 \
  --name manager-approval \
  --input true
```

If the worker crashes between `ReserveInventory` succeeding and
`ChargePayment` starting, the event history already recorded
`ReserveInventory`'s completion; when a worker resumes polling the
`order-fulfillment-tq` task queue, the workflow replays from history
(skipping straight past the already-completed reservation without
re-running it) and re-enters at the `ChargePayment` call — no manual
recovery script, no separate "resume from checkpoint" logic, and no
duplicate inventory reservation.

## Cross-references

- [temporal-configuration-validation](../temporal-configuration-validation/SKILL.md) — validating this workflow's task queue, timeout/retry, and namespace configuration before it reaches production.
- [airflow-dag-authoring-and-validation](../airflow-dag-authoring-and-validation/SKILL.md) — the scheduled, tabular batch-pipeline model to reach for instead of Temporal when the problem is a recurring data job, not a long-running stateful application process.
- [dagster-and-prefect-pipeline-authoring](../dagster-and-prefect-pipeline-authoring/SKILL.md) — the asset-based batch-orchestration alternative, with the same scheduled-data-pipeline scope distinction from Temporal described in this skill's Purpose section.
- [rabbitmq-configuration](../rabbitmq-configuration/SKILL.md) — a message-broker-based alternative worth comparing against Temporal's signal mechanism when the interaction is a simple fire-and-forget event rather than a durable, replayable workflow step.
