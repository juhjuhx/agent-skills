---
name: mlflow-experiment-tracking-and-model-registry
description: >
  Sets up and operates MLflow specifically — tracking server deployment and
  backend/artifact store choices, Model Registry stage transitions
  (Staging/Production/Archived) and the newer alias-based promotion model,
  MLproject definitions for reproducible runs, framework autologging, and
  self-hosted vs. Databricks-managed deployment tradeoffs. Use when the user
  asks to "stand up an MLflow tracking server," "configure MLflow's backend
  store," "promote a model version to Production in MLflow," "write an
  MLproject file," "enable MLflow autologging for scikit-learn/PyTorch/
  XGBoost," or "decide between self-hosted MLflow and Databricks-managed
  MLflow."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: mlops
  maturity: stable
---

# MLflow Experiment Tracking and Model Registry

## Purpose

MLflow is the most widely deployed open-source experiment tracking and model
lifecycle tool, built around four components: **Tracking** (params/metrics/
artifacts per run), **Projects** (a packaging format for reproducible runs),
**Models** (a standard packaging format with framework "flavors"), and the
**Model Registry** (versioned models with stage/lifecycle metadata). This
skill covers MLflow's specific mechanics — how the tracking server is
deployed, what a backend store actually is, how registry stage transitions
work, how autologging hooks into training frameworks, and how self-hosted
deployment differs operationally from Databricks-managed MLflow. It does not
repeat the vendor-neutral case for experiment tracking itself, which is
covered in [experiment-tracking](../experiment-tracking/SKILL.md) — read that
first if the question is "why track experiments," not "how does MLflow do
it."

## When to use

- Standing up a new MLflow tracking server and choosing a backend store
  (SQLite/Postgres/MySQL) and artifact store (S3/GCS/Azure Blob/NFS).
- Registering a trained model to the Model Registry and moving it through
  `Staging` → `Production` → `Archived`, or adopting the newer alias/tag
  model that supersedes stages in recent MLflow versions.
- Writing or debugging an `MLproject` file so a training run is reproducible
  by `mlflow run` on another machine or in CI.
- Wiring up `mlflow.autolog()` or a framework-specific autolog call
  (scikit-learn, PyTorch, XGBoost, TensorFlow/Keras, LightGBM) and
  diagnosing why expected params/metrics aren't appearing.
- Deciding whether to run self-hosted MLflow (own tracking server, own
  database, own artifact store) or use Databricks-managed MLflow, and what
  operational burden each implies.
- Troubleshooting a tracking server that's slow, a UI that can't render
  artifacts, or a registry transition that silently didn't take effect.

## Prerequisites & environment

- MLflow ≥ 2.9 if relying on the alias-based registry model described below;
  MLflow ≥ 2.x generally for the autologging flavors covered here. Behavior
  around Model Registry stages has shifted across 2.x releases — pin and
  check the installed version (`mlflow --version`) before assuming a given
  API is available.
- A backend store: `sqlite:///...` for local/single-user experimentation
  only, or a real SQLAlchemy-compatible database
  (`postgresql://`, `mysql://`) for any shared/team/production tracking
  server. The plain local file store (`./mlruns`, MLflow's zero-config
  default) does not support the Model Registry and is unsafe under
  concurrent writers.
- An artifact store separate from the backend store: S3, GCS, Azure Blob
  Storage, or an NFS mount — something durable and reachable by every
  client and by the tracking server itself.
- Network access from training clients to the tracking server's HTTP
  endpoint (default port `5000`), and from the tracking server to both the
  backend database and the artifact store.
- For self-hosted deployments needing access control: MLflow's built-in
  basic-auth plugin (`mlflow server --app-name basic-auth`) or a reverse
  proxy handling authn/authz — MLflow does not enforce authentication by
  default.
- For Databricks-managed MLflow: a Databricks workspace, and (if using
  Unity Catalog as the registry backend) Unity Catalog enabled with
  appropriate catalog/schema permissions.

## Step-by-step guidance

1. **Choose and start a real backend store before anyone treats the
   tracking server as shared infrastructure.** The default file store works
   for a single developer's local experiments but has no Model Registry
   support and corrupts under concurrent writers:
   ```bash
   mlflow server \
     --backend-store-uri postgresql://mlflow:${MLFLOW_DB_PASSWORD}@mlflow-db.internal:5432/mlflow \
     --default-artifact-root s3://ml-artifacts-<ACCOUNT_ID>/mlflow \
     --host 0.0.0.0 \
     --port 5000
   ```
   The backend store holds run metadata (params, metrics, tags, registry
   entries); the artifact store holds the actual files (models, plots,
   checkpoints). They are configured separately and can point at entirely
   different systems.

2. **Point training clients at the tracking server**, not a local path:
   ```python
   import mlflow

   mlflow.set_tracking_uri("http://mlflow.internal:5000")
   mlflow.set_experiment("fraud-scorer")
   ```

3. **Use autologging to instrument standard training calls** with minimal
   code changes, then add manual logging only for what autolog doesn't
   capture:
   ```python
   import mlflow
   import mlflow.xgboost
   import xgboost as xgb

   mlflow.xgboost.autolog()  # or mlflow.sklearn.autolog(), mlflow.pytorch.autolog(), etc.

   with mlflow.start_run(run_name="xgb-baseline"):
       model = xgb.train(params, dtrain, evals=[(dval, "validation")])
       # autolog already captured params, per-iteration eval metrics, and
       # the model artifact; add anything autolog can't infer:
       mlflow.log_metric("business_precision_at_1pct_fpr", custom_metric)
   ```
   The generic `mlflow.autolog()` enables autologging for every supported
   flavor installed in the environment; call the framework-specific
   version (`mlflow.sklearn.autolog()`) when only one framework is in use
   to avoid surprises from unrelated libraries also being instrumented.
   Autolog only instruments the framework's own training entry points
   (`.fit()`, `xgb.train()`, a Keras `.fit()` loop) — a fully custom
   training loop that doesn't call through those APIs won't be captured
   and needs manual `mlflow.log_metric`/`log_param` calls.

4. **Package training as an MLproject for anyone (or any CI job) to
   reproduce the exact run:**
   ```yaml
   # MLproject
   name: fraud-scorer

   python_env: python_env.yaml

   entry_points:
     main:
       parameters:
         max_depth: {type: int, default: 6}
         learning_rate: {type: float, default: 0.05}
         data_snapshot: {type: string, default: "s3://data-lake/fraud/snapshots/latest"}
       command: >
         python train.py --max-depth {max_depth} --learning-rate {learning_rate}
         --data-snapshot {data_snapshot}
   ```
   ```yaml
   # python_env.yaml — pin exact versions, not ranges, for reproducibility
   python: "3.11.6"
   dependencies:
     - mlflow==2.16.2
     - xgboost==2.1.1
     - pandas==2.2.2
   ```
   ```bash
   mlflow run . -P max_depth=8 -P learning_rate=0.03 \
     --experiment-name fraud-scorer
   ```
   `mlflow run` recreates the declared environment before executing the
   entry point, so the run is reproducible by someone who has never seen
   the training script's ad hoc setup steps.

5. **Register the winning run's model artifact to the Model Registry**:
   ```python
   result = mlflow.register_model(
       model_uri="runs:/<RUN_ID>/model",
       name="fraud-scorer",
   )
   ```

6. **Move a registered version through its lifecycle deliberately.** The
   classic stage model (`None` → `Staging` → `Production` → `Archived`)
   is being superseded by a tag/alias-based model starting around MLflow
   2.9 — check which your server version and client expect:
   ```python
   from mlflow import MlflowClient

   client = MlflowClient()

   # Classic stage-based transition (still supported, deprecated path):
   client.transition_model_version_stage(
       name="fraud-scorer",
       version=14,
       stage="Staging",
       archive_existing_versions=False,
   )

   # Newer alias-based promotion (recommended on MLflow >= 2.9):
   client.set_registered_model_alias(name="fraud-scorer", alias="champion", version=14)
   client.set_registered_model_alias(name="fraud-scorer", alias="challenger", version=15)
   ```
   Aliases are mutable pointers (like a Git tag) rather than a fixed
   enum, so a team can define its own promotion vocabulary
   (`champion`/`challenger`, `canary`/`stable`) instead of being locked
   into `Staging`/`Production`/`Archived`.

   > **Warning — promoting a version straight to `Production`/`champion`
   > without a rollback plan is a risky action.** Before transitioning,
   > confirm: (a) which version is currently serving and can be restored
   > by re-pointing the alias or re-transitioning it back, (b) that the
   > previous version's artifact and run are still retained (not
   > archived-and-deleted), and (c) that there is a fast, tested path to
   > revert if the new version misbehaves under real traffic. Treat a
   > registry promotion with no documented rollback the same as a
   > production deploy with `autoRollbackConfiguration` disabled — do not
   > present it as a routine, low-risk action.

7. **Serve or load a specific registered version explicitly by
   version/alias**, never "whatever is latest" implicitly:
   ```python
   model = mlflow.pyfunc.load_model("models:/fraud-scorer@champion")
   # or, pinned to an explicit version:
   model = mlflow.pyfunc.load_model("models:/fraud-scorer/14")
   ```

8. **Decide self-hosted vs. Databricks-managed deliberately, based on
   operational capacity, not default inertia:**
   - **Self-hosted** (`mlflow server` on your own compute, own Postgres/
     MySQL, own S3/GCS bucket): full control over cost and data locality,
     but your team owns HA, backups of the backend database, artifact
     store lifecycle policies, and access control (MLflow's own
     authentication is basic; most teams front it with a reverse proxy or
     SSO gateway).
   - **Databricks-managed MLflow**: tracking server, registry, and
     (optionally) Unity-Catalog-backed model governance are operated by
     Databricks, integrated with Databricks workspace permissions and
     compute — removes the server/database/HA operational burden, at the
     cost of coupling the workflow to the Databricks platform and its
     pricing/access model.
   - A team without dedicated platform engineering capacity to patch,
     back up, and scale a tracking server should default to managed;
     a team with strict data-residency or cost constraints that already
     operates Postgres/S3 in-house has a straightforward self-hosted path.

## Best practices

- Never point a shared tracking server at the default local file store —
  require a real database backend store for anything more than one
  developer's throwaway experiments.
- Keep the artifact store durable and independent of the tracking server's
  own compute (S3/GCS/Blob, not local disk on an ephemeral instance) so a
  server restart or autoscaling event doesn't lose logged models.
- Prefer framework-specific `autolog()` calls over the blanket
  `mlflow.autolog()` in shared training code, so enabling MLflow for one
  framework doesn't silently start instrumenting an unrelated library also
  imported in the same process.
- Pin exact dependency versions in `MLproject`'s environment file — a
  range-pinned or unpinned dependency defeats the reproducibility
  `mlflow run` is meant to provide.
- Use aliases (or well-documented stage conventions) consistently across
  the team, and always carry the originating run ID as a registry tag, so
  [experiment-tracking](../experiment-tracking/SKILL.md)'s guidance on
  reproducibility and audit trail applies end-to-end from run to registered
  model.
- Restrict who/what can call `transition_model_version_stage` or
  `set_registered_model_alias` for the `Production`/`champion` designation
  to a controlled release process (CI job, on-call approval), not any
  script with registry write access.

## Common pitfalls

- **Symptom:** A team starts logging to MLflow's default local `./mlruns`
  file store from multiple machines/CI jobs, and runs occasionally go
  missing or the store becomes corrupted.
  **Fix:** Stand up a real tracking server backed by Postgres/MySQL before
  more than one process writes concurrently — the file store has no
  concurrency guarantees and no Model Registry support.

- **Symptom:** A model version is transitioned straight to `Production`
  (or aliased `champion`) right after training, it turns out to regress a
  key metric under real traffic, and there's no quick way back because the
  previous version's alias was overwritten with no record of what it was.
  **Fix:** Before promoting, record which version is being replaced (query
  `get_model_version_by_alias` first), keep that version's artifact
  un-archived, and have a tested one-line rollback
  (`set_registered_model_alias` back to the prior version) ready — never
  promote without knowing the exact revert step.

- **Symptom:** `mlflow.autolog()` is called in a custom PyTorch training
  loop that doesn't use a supported `Trainer` abstraction, and expected
  per-epoch metrics never show up in the run.
  **Fix:** Autologging only instruments the framework's own recognized
  entry points; for a fully custom loop, either restructure it to use a
  supported wrapper (e.g. a Lightning `Trainer`) or add explicit
  `mlflow.log_metric` calls inside the loop instead of assuming autolog
  covers it.

- **Symptom:** `mlflow run .` fails on a teammate's machine with a
  dependency resolution error, even though it worked for the original
  author.
  **Fix:** The `MLproject`'s environment file used unpinned or
  range-pinned dependencies; pin exact versions (`mlflow==2.16.2`, not
  `mlflow>=2.0`) so the recreated environment matches what actually
  produced the original run's results.

- **Symptom:** The tracking server's artifact store fills up with
  thousands of large checkpoint artifacts from abandoned exploratory runs,
  and storage costs climb steadily.
  **Fix:** Apply a retention/lifecycle policy at the artifact store level
  (e.g. S3 lifecycle rules) for experiments tagged as exploratory, while
  explicitly excluding any run referenced by a current registry entry —
  consistent with the retention guidance in
  [experiment-tracking](../experiment-tracking/SKILL.md); never let a
  blanket age-based deletion rule reach a run backing a production model.

## Worked example

**Scenario:** A team self-hosts MLflow for a fraud-scoring model, using
Postgres as the backend store and S3 as the artifact store, with
XGBoost autologging and alias-based registry promotion.

1. Tracking server, started once as shared infrastructure:
   ```bash
   mlflow server \
     --backend-store-uri postgresql://mlflow:${MLFLOW_DB_PASSWORD}@mlflow-db.internal:5432/mlflow \
     --default-artifact-root s3://ml-artifacts-<ACCOUNT_ID>/mlflow \
     --host 0.0.0.0 --port 5000
   ```
2. Training script, run via `mlflow run` for reproducibility, with
   XGBoost autologging enabled:
   ```python
   import mlflow, mlflow.xgboost, xgboost as xgb

   mlflow.set_tracking_uri("http://mlflow.internal:5000")
   mlflow.set_experiment("fraud-scorer")
   mlflow.xgboost.autolog()

   with mlflow.start_run(run_name="xgb-depth6-lr0.05") as run:
       model = xgb.train(
           {"max_depth": 6, "eta": 0.05, "objective": "binary:logistic"},
           dtrain, evals=[(dval, "validation")], num_boost_round=300,
       )
       mlflow.log_param("data_snapshot", "s3://data-lake/fraud/snapshots/2026-07-20")
   run_id = run.info.run_id
   ```
3. Registration and alias-based promotion, run as a controlled step
   after the run's metrics clear a review bar (not automatically):
   ```python
   from mlflow import MlflowClient

   client = MlflowClient()
   mv = mlflow.register_model(f"runs:/{run_id}/model", "fraud-scorer")

   # Record the currently-promoted version before touching the alias,
   # so there's an explicit rollback target.
   previous_champion = client.get_model_version_by_alias("fraud-scorer", "champion")
   print(f"current champion is version {previous_champion.version} — rollback target if needed")

   client.set_registered_model_alias("fraud-scorer", "champion", mv.version)
   ```
4. Serving code loads the alias, never a hardcoded version, so the next
   promotion doesn't require a code change:
   ```python
   model = mlflow.pyfunc.load_model("models:/fraud-scorer@champion")
   ```
5. Two weeks later the new champion's live precision drops; on-call
   reverts with the recorded previous version:
   ```python
   client.set_registered_model_alias("fraud-scorer", "champion", previous_champion.version)
   ```
   because step 3 captured the rollback target before promoting, this is
   a one-line fix rather than an incident-time scramble.

## Cross-references

- [experiment-tracking](../experiment-tracking/SKILL.md) — the
  vendor-neutral case for tracking runs, tagging conventions, and
  reproducibility that this skill implements in MLflow-specific terms.
- [weights-and-biases-experiment-tracking](../weights-and-biases-experiment-tracking/SKILL.md) —
  the comparable SaaS-first tool; see its Cross-references section for
  how to choose between the two.
- [model-packaging-and-versioning](../model-packaging-and-versioning/SKILL.md) —
  broader model packaging/versioning concerns beyond the Model Registry's
  stage/alias mechanics covered here.
- [training-pipeline-orchestration](../training-pipeline-orchestration/SKILL.md) —
  how an `MLproject`-style training run fits into an orchestrated
  pipeline rather than being invoked ad hoc.
