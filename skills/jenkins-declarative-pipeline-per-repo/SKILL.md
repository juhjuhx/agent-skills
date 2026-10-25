---
name: jenkins-declarative-pipeline-per-repo
description: >
  Authors and troubleshoots a per-repo Jenkinsfile using Jenkins Declarative
  Pipeline syntax — agent, stages, steps, post, environment, and when blocks
  — for a single repository's own build/test/deploy flow. Use when the user
  asks to "write a Jenkinsfile," "add a declarative pipeline to this repo,"
  "fix a failing Jenkins stage," "add a post-build notification to Jenkins,"
  or "set up per-repo CI in Jenkins" without a shared organization-wide
  library.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: cicd-tooling
  maturity: stable
---

# Jenkins Declarative Pipeline Per Repo

## Purpose

A per-repo `Jenkinsfile` puts pipeline-as-code directly in the repository it
builds: it's reviewed in the same pull request as the code change, versioned
alongside it, and doesn't require a Jenkins administrator to touch a
separate job configuration. This skill covers Jenkins **Declarative
Pipeline** syntax specifically — the `agent`/`stages`/`steps`/`post` block
structure, `environment` and `when` conditionals, and the concrete
constructs (not generic CI concepts, which are covered in
[ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md))
needed to write a correct, maintainable Jenkinsfile that lives in a single
repo. It also covers the specific trade-off of the per-repo model versus
centralizing logic in a shared library, so a team can make an informed
choice rather than defaulting to copy-paste.

## When to use

- A repository has no Jenkinsfile yet and needs one for build/test/package.
- An existing per-repo Jenkinsfile is failing at a specific stage and needs
  debugging (syntax error, wrong `agent` label, a `when` condition that
  never matches).
- Adding a `post` block for Slack/email notification on failure, or a
  `always` cleanup step (e.g. `deleteDir()`), to an existing pipeline.
- Deciding whether pipeline logic that's growing complex in one Jenkinsfile
  should stay per-repo or be extracted into a shared library — see
  [jenkins-centralized-shared-library](../jenkins-centralized-shared-library/SKILL.md)
  for that migration.
- Reviewing a Jenkinsfile PR and needing to know whether `sh`, `script`, or
  a plugin step is idiomatic for a given task.

## Prerequisites & environment

- A Jenkins controller (2.401+ LTS recommended for current Declarative
  Pipeline features) with the **Pipeline** plugin suite installed
  (`workflow-aggregator`), which ships Declarative Pipeline support.
- The repo is registered as a **Multibranch Pipeline** or **Pipeline job
  with "Pipeline script from SCM"** pointing at `Jenkinsfile` in the repo
  root (or a path configured in the job) — the Jenkinsfile is not useful
  without a job/multibranch config that reads it from SCM.
- Build agents (nodes) with the required labels available — e.g. a `docker`
  or `linux-x64` label matching what the Jenkinsfile's `agent` block
  requests. Confirm labels via **Manage Jenkins → Nodes**.
- Credentials (SSH keys, registry tokens, cloud creds) already created in
  **Manage Jenkins → Credentials** with known IDs — a Jenkinsfile only
  references a credential ID (`${JENKINS_CRED_ID}`), it never stores the
  secret value itself.
- For Docker-based agents: the controller/agent has Docker available and
  the `Docker Pipeline` plugin installed if using `agent { docker { ... } }`.

## Step-by-step guidance

1. **Start from the top-level `pipeline` block** — Declarative Pipeline
   requires exactly one `pipeline { }` block; you cannot mix bare Scripted
   Pipeline steps at the top level.

   ```groovy
   pipeline {
       agent any
       options {
           timestamps()
           timeout(time: 30, unit: 'MINUTES')
           disableConcurrentBuilds()
       }
       environment {
           IMAGE_NAME = 'registry.example.com/myapp'
       }
       stages {
           stage('Checkout') {
               steps {
                   checkout scm
               }
           }
       }
   }
   ```

2. **Pin `agent` precisely, not just `agent any`.** Use a label for a
   specific node pool, or a `docker` agent for a reproducible toolchain
   pinned by image tag:

   ```groovy
   agent {
       docker {
           image 'node:20.11-bullseye'
           args '-v $HOME/.npm:/home/node/.npm'
       }
   }
   ```
   `agent any` is fine for a small team with a homogeneous fleet; pin a
   label or Docker image once tooling versions must be reproducible or
   multiple agent types exist.

3. **Model real stages, not one giant `script` block.** Each logical phase
   (checkout, build, test, package, deploy) is its own `stage`, so the
   Jenkins UI/API shows per-stage pass/fail and timing:

   ```groovy
   stages {
       stage('Build') {
           steps { sh 'npm ci && npm run build' }
       }
       stage('Test') {
           steps { sh 'npm test -- --reporter=junit --output=reports/junit.xml' }
           post {
               always {
                   junit 'reports/junit.xml'
               }
           }
       }
       stage('Package') {
           steps {
               sh 'docker build -t ${IMAGE_NAME}:${GIT_COMMIT} .'
           }
       }
       stage('Deploy to staging') {
           when {
               branch 'main'
           }
           steps {
               withCredentials([usernamePassword(credentialsId: '${JENKINS_CRED_ID}',
                                                  usernameVariable: 'REG_USER',
                                                  passwordVariable: 'REG_PASS')]) {
                   sh '''
                     echo "$REG_PASS" | docker login registry.example.com -u "$REG_USER" --password-stdin
                     docker push ${IMAGE_NAME}:${GIT_COMMIT}
                   '''
               }
           }
       }
   }
   ```

4. **Use `when` for conditional stages instead of shell-level `if` guards**
   so skipped stages show clearly as "skipped" in the UI rather than as a
   confusing green no-op:
   ```groovy
   when {
       allOf {
           branch 'main'
           not { changeRequest() }
       }
   }
   ```

5. **Drop into `script { }` only for real Groovy logic** (loops,
   conditionals on computed values) that the declarative DSL can't express
   directly — keep these blocks small; anything non-trivial belongs in a
   shared library function, see
   [jenkins-centralized-shared-library](../jenkins-centralized-shared-library/SKILL.md).
   ```groovy
   steps {
       script {
           def version = sh(script: 'git describe --tags --always', returnStdout: true).trim()
           env.BUILD_VERSION = version
       }
   }
   ```

6. **Add `post` for outcome-based actions** — notification, cleanup,
   artifact archiving — always at the pipeline level (and per-stage where
   needed):
   ```groovy
   post {
       success {
           slackSend(channel: '#builds', color: 'good', message: "Build ${env.BUILD_NUMBER} succeeded")
       }
       failure {
           slackSend(channel: '#builds', color: 'danger', message: "Build ${env.BUILD_NUMBER} failed: ${env.BUILD_URL}")
       }
       always {
           archiveArtifacts artifacts: 'dist/**', allowEmptyArchive: true
           cleanWs()
       }
   }
   ```

7. **Validate syntax before pushing** using the Jenkins CLI or the
   `Jenkinsfile` linter endpoint:
   ```bash
   curl -s -X POST -u ${JENKINS_USER}:${JENKINS_API_TOKEN} \
     -F "jenkinsfile=<Jenkinsfile" \
     https://jenkins.example.com/pipeline-model-converter/validate
   ```
   Catching a `WorkflowScript: 12: Expected one of ...` error here is far
   faster than waiting for a real build to fail at parse time.

## Best practices

- Keep the Jenkinsfile declarative end-to-end; reach for `script {}` only
  for logic the DSL genuinely can't express, and keep those blocks under
  ~10 lines — anything bigger is a sign the logic belongs in a shared
  library function instead of inline Groovy (see
  [jenkins-groovy-scripting-best-practices](../jenkins-groovy-scripting-best-practices/SKILL.md)).
- Set `options { timeout(...) }` and `disableConcurrentBuilds()` (or
  `options { skipDefaultCheckout() }` where appropriate) explicitly — a
  Jenkinsfile with no timeout can hang a stuck agent indefinitely, tying up
  an executor.
- Reference credentials only by ID (`withCredentials`, `credentialsId:`),
  never inline — Jenkins masks values referenced this way in console
  output automatically; a value assigned to a plain `env` var from a
  credential is not masked.
- Use `junit`/`archiveArtifacts`/`recordIssues` (Warnings Next Generation
  plugin) to surface structured results in the Jenkins UI rather than only
  a pass/fail exit code — this mirrors the "fail fast and make failures
  actionable" guidance in
  [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md).
- Decide early whether logic is genuinely repo-specific (belongs inline)
  or organization-wide (belongs in a shared library) — a Jenkinsfile that
  has grown past ~150 lines of duplicated logic across many repos is the
  signal to migrate, see
  [jenkins-centralized-shared-library](../jenkins-centralized-shared-library/SKILL.md).
- Version-pin plugin-provided steps where the plugin has known breaking
  changes between major versions (check the plugin's changelog before a
  Jenkins upgrade), since a per-repo Jenkinsfile has no central place to
  absorb a plugin API change across many repos.

## Common pitfalls

- **Symptom:** Pipeline fails immediately with
  `WorkflowScript: 3: Expected one of "pipeline", ... @ line 3, column 1`.
  **Fix:** Declarative Pipeline requires the single top-level `pipeline {}`
  block with no bare Groovy statements or Scripted-style `node {}` outside
  it; move any Scripted-style code inside a `script {}` block within a
  `steps` block.

- **Symptom:** `deploy` stage runs on every branch, including feature
  branches, even though it's "supposed to" only run on `main`.
  **Fix:** Add an explicit `when { branch 'main' }` (or `when { allOf {
  branch 'main'; not { changeRequest() } } }`) to the stage — without it, a
  Multibranch Pipeline job runs every stage on every discovered branch.

- **Symptom:** A credential value shows up in plaintext in the build
  console log.
  **Fix:** Never assign a credential to a plain environment variable via
  `environment { TOKEN = credentials('id') }` followed by manual `echo`, and
  never `sh "curl -H Authorization: ${TOKEN}"` without quoting through
  `withCredentials`'s masked bindings — use `withCredentials([...])` and
  keep the secret variable inside its scope; Jenkins only masks values it
  knows are secret-bound in that block.

- **Symptom:** Build hangs for hours consuming an executor after an agent
  goes unresponsive mid-`sh` step.
  **Fix:** Add `options { timeout(time: 30, unit: 'MINUTES') }` at the
  pipeline or stage level so a stuck step is killed and the executor freed
  instead of blocking indefinitely.

- **Symptom:** Two builds of the same branch run concurrently and race on
  a shared resource (e.g. both push to the same tag).
  **Fix:** Add `options { disableConcurrentBuilds() }`, or narrow it with
  `disableConcurrentBuilds(abortPrevious: true)` (Jenkins 2.263+) so a new
  build cancels the superseded one rather than running in parallel.

## Worked example

**Scenario:** A single Node.js service repo needs its own Jenkinsfile:
lint/test on every branch and PR, Docker build + push to a registry only on
`main`, with Slack notification on failure.

`Jenkinsfile` (repo root):
```groovy
pipeline {
    agent {
        docker { image 'node:20.11-bullseye' }
    }
    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds(abortPrevious: true)
    }
    environment {
        IMAGE_NAME = 'registry.example.com/myapp'
    }
    stages {
        stage('Install & Lint') {
            steps {
                sh 'npm ci'
                sh 'npm run lint'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test -- --reporter=junit --outputFile=reports/junit.xml'
            }
            post {
                always { junit 'reports/junit.xml' }
            }
        }
        stage('Build & Push image') {
            when { branch 'main' }
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${GIT_COMMIT} .'
                withCredentials([usernamePassword(credentialsId: '${JENKINS_CRED_ID}',
                                                   usernameVariable: 'REG_USER',
                                                   passwordVariable: 'REG_PASS')]) {
                    sh '''
                      echo "$REG_PASS" | docker login registry.example.com -u "$REG_USER" --password-stdin
                      docker push ${IMAGE_NAME}:${GIT_COMMIT}
                    '''
                }
            }
        }
    }
    post {
        failure {
            slackSend(channel: '#builds', color: 'danger',
                      message: "FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER} (${env.BUILD_URL})")
        }
        always {
            cleanWs()
        }
    }
}
```
This runs identically whether triggered by a PR or a `main` push, only
gating the image push stage with `when { branch 'main' }`, and keeps the
registry credential scoped to the one `withCredentials` block that needs it.

## Cross-references

- [jenkins-centralized-shared-library](../jenkins-centralized-shared-library/SKILL.md) — extract logic here into an org-wide shared library once it's duplicated across repos.
- [jenkins-groovy-scripting-best-practices](../jenkins-groovy-scripting-best-practices/SKILL.md) — writing safe, testable Groovy inside `script {}` blocks.
- [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md) — vendor-neutral stage layout, caching, and gating concepts this Jenkinsfile implements.
- [secure-cicd-gates](../../../devsecops/skills/secure-cicd-gates/SKILL.md) — designing the security scan stages to add into this pipeline.
