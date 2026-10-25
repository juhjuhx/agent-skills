---
name: experiment-tracking
description: >
  Guides setting up experiment tracking for ML training runs — logging
  params, metrics, artifacts, and code/data versions so results are
  comparable and reproducible. Use when the user asks to "track experiments",
  set up MLflow/Weights & Biases/Neptune/DVC, compare training runs, reproduce
  a past experiment, organize hyperparameter sweeps, or figure out why a
  training run can't be reproduced.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: mlops
  maturity: stable
---

# Experiment Tracking

## Purpose

ML development is fundamentally iterative — dozens or hundreds of training
runs with varying data, hyperparameters, and code, most of which don't become
the production model. Without experiment tracking, this iteration produces an
unmanageable pile of scripts, spreadsheets, and "I think this was the run
that worked" guesses. Experiment tracking makes every run a structured,
comparable, reproducible record: exact parameters, resulting metrics, logged
artifacts, and a link back to the code and data version that produced it.
This matters operationally because it's the difference between being able to
answer "why did we choose this model" and "can we reproduce it" months later,
versus not.

## When to use

- The user is setting up or choosing an experiment tracking tool (MLflow,
  Weights & Biases, Neptune, ClearML, Comet, or a DVC-based approach).
- The user wants to compare multiple training runs (different hyperparameters,
  architectures, or datasets) systematically.
- The user is running or planning a hyperparameter sweep/search.
- The user needs to reproduce a past experiment and is missing some of the
  context (params, data version, code version) needed to do so.
- The user wants to link experiment runs to the artifacts they produced for
  registration (see
  [model-packaging-and-versioning](../model-packaging-and-versioning/SKILL.md)).
- The user is debugging "why is this run's result different from last time
  with the same config."

## Prerequisites & environment

- A tracking backend: MLflow ≥ 2.x (self-hosted or managed), Weights & Biases,
  Neptune, or ClearML — any of these support params/metrics/artifact logging
  and a comparison UI.
- Instrumented training code that can log to the chosen backend (usually a
  few SDK calls added around the training loop).
- A version control system (git) for training code, and a data versioning
  scheme (dataset snapshot IDs, DVC, or Delta Lake table versions) for
  training data — experiment tracking is only as reproducible as the code
  and data versions it references.
- Storage for artifacts (model checkpoints, plots, sample predictions) —
  typically the tracking backend's own artifact store (S3/GCS-backed) or
  the model registry itself.
- Consistent run-naming/tagging conventions agreed on by the team before
  runs start accumulating — retrofitting tags onto hundreds of untagged past
  runs is painful.

## Step-by-step guidance

1. **Log parameters, metrics, and artifacts for every run** — not just the
   ones that "worked." Cheap runs are cheap to log; expensive ones are
   exactly the ones you'll regret not logging if something looks off later.
   ```python
   import mlflow

   mlflow.set_experiment("fraud-scorer")

   with mlflow.start_run(run_name="gbdt-depth6-lr0.05"):
       mlflow.log_params({
           "model_type": "gradient_boosted_trees",
           "max_depth": 6,
           "learning_rate": 0.05,
           "n_estimators": 300,
           "data_snapshot": "s3://data-lake/fraud/snapshots/2026-07-20",
           "git_sha": "a1b2c3d",
       })

       model = train(...)
       metrics = evaluate(model, val_set)

       mlflow.log_metrics({
           "auc": metrics["auc"],
           "precision_at_1pct_fpr": metrics["precision_at_1pct_fpr"],
           "train_loss_final": metrics["train_loss_final"],
       })

       mlflow.log_artifact("confusion_matrix.png")
       mlflow.sklearn.log_model(model, artifact_path="model")
   ```
2. **Log the exact code and data versions**, not just a description —
   `git_sha` for code, a content-addressed or timestamped snapshot ID for
   data. Tie this in with lineage tracking (see
   [data-and-model-lineage](../data-and-model-lineage/SKILL.md)) so a run's
   full provenance is queryable, not just its hyperparameters.
3. **Adopt a consistent tagging scheme** across the team: e.g. tags for
   `owner`, `purpose` (baseline/sweep/ablation/production-candidate), and
   `dataset_version`, so runs are filterable months later without relying on
   memory.
4. **Use the tracker for hyperparameter sweeps**, logging each trial as its
   own run under a shared parent/sweep ID:
   ```python
   import itertools
   import mlflow

   mlflow.set_experiment("fraud-scorer-sweep")

   for max_depth, lr in itertools.product([4, 6, 8], [0.01, 0.05, 0.1]):
       with mlflow.start_run(run_name=f"depth{max_depth}-lr{lr}"):
           mlflow.log_params({"max_depth": max_depth, "learning_rate": lr,
                               "sweep_id": "sweep-2026-07-21"})
           metrics = train_and_evaluate(max_depth=max_depth, learning_rate=lr)
           mlflow.log_metrics(metrics)
   ```
5. **Compare runs via the tracker's UI/API rather than ad hoc spreadsheets**
   — filter/sort by metric, and pin the top candidates for deeper review
   rather than manually copy-pasting numbers between runs.
6. **Promote the winning run's artifact to the model registry explicitly**,
   carrying over its run ID as a permanent tag so the registered model
   version always links back to the exact experiment that produced it (see
   [model-packaging-and-versioning](../model-packaging-and-versioning/SKILL.md)).
7. **Set a retention/archival policy for experiment data** — don't let
   artifact storage grow unbounded, but never delete the run that backs the
   currently-registered production model or any run still referenced by
   lineage records; archive old, unused runs rather than deleting outright
   if there's any ambiguity about what's still referenced.
8. **Re-run a "reproduce" check periodically** for at least the current
   production model's originating run — pull its logged code SHA, data
   snapshot, and params, and confirm re-running produces materially the same
   metrics. Treat a failed reproduction as a process bug to fix, not an
   inherent limitation to shrug off.

## Best practices

- Log more than you think you need — extra metrics and artifacts are cheap
  to store and expensive to regenerate after the fact.
- Make logging automatic (a training wrapper/decorator) rather than relying
  on every script author to remember to call the logging API correctly and
  consistently.
- Separate "spam" exploratory runs from candidate runs using an experiment
  namespace or tag, so the comparison view for "what are we choosing between"
  isn't cluttered with hundreds of throwaway trials.
- Store enough information in each run to answer "could someone else on the
  team rerun this from scratch" — code version, data version, environment
  (container image or locked dependency file), and full hyperparameters.
- Treat experiment tracking metadata as an audit trail relevant to
  compliance/governance, not merely a developer convenience — for regulated
  use cases, "which data and code produced this production model" needs to
  be answerable definitively.
- Prefer structured metric names and units (`auc`, `precision_at_1pct_fpr`)
  applied consistently across runs and projects, so cross-project comparison
  and dashboarding doesn't require manual cleanup.

## Common pitfalls

- **Symptom:** Months after a model was chosen, no one can reproduce the
  winning run's result — the code has moved on and the exact data snapshot
  used is unclear.
  **Fix:** Log the git SHA and a concrete, immutable data version/snapshot
  ID (not "the data as of that time," which is not retrievable later) on
  every run at logging time, not reconstructed after the fact.

- **Symptom:** A hyperparameter sweep produces 200 runs with generic names
  (`run_1`, `run_2`, ...) and no tags, and comparing them requires manually
  opening each one.
  **Fix:** Agree on and enforce a tagging/naming convention before the sweep
  starts (sweep ID, varied hyperparameters in the run name, owner), and log
  all varied parameters as first-class logged params so the UI's comparison
  view can filter/sort on them directly.

- **Symptom:** Two runs with what looks like an identical config produce
  different metrics, and it turns out one used a slightly different
  (uncommitted) local code change that was never logged anywhere.
  **Fix:** Fail the run (or at minimum flag it prominently) if there are
  uncommitted local changes at run start, rather than silently logging a git
  SHA that doesn't reflect the code that actually ran; make "clean working
  tree" a precondition for any run intended to be reproducible/comparable.

- **Symptom:** A well-meaning cleanup deletes "old" experiment runs and
  artifacts to save storage costs, and it turns out one of the deleted runs
  was the originating record for the currently-deployed production model,
  breaking the audit trail.
  **Fix:** Never delete experiment runs without cross-checking whether
  they're referenced by an active model registry entry or lineage record;
  archive to cold storage instead of hard-deleting, and treat deletion of
  any run tied to a production artifact as requiring explicit, warned
  confirmation.

## Worked example

A team runs a hyperparameter sweep to improve `fraud-scorer`.

1. They create an MLflow experiment `fraud-scorer-sweep-2026-07`, and log a
   9-trial grid sweep over `max_depth ∈ {4,6,8}` and
   `learning_rate ∈ {0.01,0.05,0.1}`, each run tagged `sweep_id=sweep-2026-07-21`,
   `git_sha=a1b2c3d`, `data_snapshot=2026-07-20`.
2. The tracker's comparison view sorts all 9 runs by `auc`; the best is
   `depth6-lr0.05` at AUC 0.912, followed closely by `depth8-lr0.05` at
   AUC 0.909 but with meaningfully higher inference latency logged as an
   artifact (a latency benchmark plot) — the team picks `depth6-lr0.05` as
   the balance of quality and serving cost.
3. This run's ID (`run-8841`) and its logged model artifact are registered
   to the model registry as `fraud-scorer` version 14 (see
   [model-packaging-and-versioning](../model-packaging-and-versioning/SKILL.md)),
   with the run ID carried over as a permanent tag on the registry entry.
4. Three months later, an auditor asks exactly what data and code produced
   the model currently in production. The team queries the registry entry
   for version 14, follows its `run_id` tag to `run-8841` in the tracker,
   and retrieves the exact git SHA, data snapshot URI, and hyperparameters
   used — answerable in minutes because the linkage was captured at
   logging time, not reconstructed after the fact.

## Cross-references

- [training-pipeline-orchestration](../training-pipeline-orchestration/SKILL.md)
- [model-packaging-and-versioning](../model-packaging-and-versioning/SKILL.md)
- [data-and-model-lineage](../data-and-model-lineage/SKILL.md)
- [llmops-fine-tuning-and-deployment](../llmops-fine-tuning-and-deployment/SKILL.md)
