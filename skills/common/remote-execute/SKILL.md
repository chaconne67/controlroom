---
name: remote-execute
description: Run reproducible heavy repository commands on a remote server for data extraction, microplan-batch verification, Playwright/screenshot checks, long tests, or expensive batch jobs.
---

# Remote Execute

Use this skill to run heavy repository commands over SSH. Follow the project's official source host and checkout; use `chaconne@49.247.45.243` when the project authorizes a separate heavy-job worker. Transfer source state through Git commits and branches; transfer large generated artifacts with `rsync`/`scp`, not Git.

## Core Rule

Development agents, planning, code-change decisions, and LLM development sessions run in the control room. The agent reads its plans and skills there, edits the official code checkout over SSH when it is remote, and sends reproducible commands to the server. Do not launch a development-agent session on the server. Established LLM API calls inside product features or batch pipelines remain part of those programs and follow their existing authorization.

Choose the path from the project's existing source location:

- **Remote source, control-room folder without code:** use SSH in the project's official remote checkout or authorized worktree for edits, tests, Git operations, and result inspection. Do not clone code into the control room to satisfy the helper's local-checkout requirement. Prepare and verify command changes in that official source checkout before dispatching a heavy job; preserve existing user changes and record the tested commit and diff.
- **Existing local code checkout:** use the bundled helper below. First make the intended local state reproducible:

1. Inspect `git status --short`.
2. Commit or explicitly exclude local changes.
3. Push a dedicated branch.
4. Run the task on the remote worker from that branch.
5. Inspect results from the control room, then issue any required remote commit and push commands.
6. Fetch and inspect Git results locally before merge/cherry-pick.
7. Download large artifacts separately only when they are needed locally.

In either path, preserve unrelated changes. If the required changes cannot be isolated safely within the approved scope, stop and ask what should be included.

If a heavy job requires a new command, option, helper script, schema, prompt, or test fixture, the control-room agent implements and verifies it in the project's official source checkout first. Commit and, when transferring to a separate worker, push that code before dispatching the heavy job. Use the project's existing development and validation path to prepare the change; the dispatched job must run code reproducible from Git.

## Standard Flow

Use the bundled helper only for the existing-local-checkout path. For the remote-source path, issue commands over SSH in the approved checkout/worktree instead; the helper's CLI and clean-local-worktree requirement remain unchanged.

`<SKILL_DIR>` means the absolute directory containing this `SKILL.md`. Resolve it from the active
skill path before running the command.

```bash
python3 "<SKILL_DIR>/scripts/remote_execute.py" \
  --command 'uv run --extra dev pytest tests/test_project_detail_layout.py -v'
```

The helper:

- requires a clean local worktree
- pushes `HEAD` to a `remote-exec/...` branch
- clones or updates the repo on the remote worker
- runs the command there
- pushes remote commits back to the same branch
- prints local fetch/merge guidance

Use Git for source code, code-coupled documents, schemas, scripts, tests, and small reports. Planning documents and development instructions stay in their control-room source. Do not commit extracted text corpora, batch JSONL outputs, PDFs, screenshots/videos, model outputs, DB dumps, or other large artifacts unless the user explicitly asks and the repo is designed for that storage.

For long-running jobs, the control-room agent sends the exact program or test command to run on the server. Prefer foreground remote execution when the current session can wait. Use background remote execution only when the job has its own progress files/logs and a clear resume path.

## Microplan Batch

For `microplan-batch` or large verification batches:

1. Keep the plan, progress tracking, and task decisions in the control room.
2. The control-room agent implements each task in the project's official source checkout and prepares the reproducible code state required by the selected execution path.
3. Execute the task's build, test, or batch program commands over SSH; the microplan agent loop remains in the control room.
4. The control-room agent reviews each task's results and issues the required Git commands in the code checkout.
5. Inspect commits and diffs in the official source checkout, using local fetch only for the existing-local-checkout path.

Do not let remote work touch production credentials, production DBs, paid external APIs, Drive/Gemini jobs, or Telegram notifications unless the user explicitly approves that external action for the remote server.

## Data Extraction

For exdigm data extraction jobs, this skill is the authoritative source for remote execution policy. Domain skills such as `data-extraction` may point here, but this section owns the rule.

In this section, `local/operational server` is the project's existing source and DB execution environment; it need not be the control-room PC. The control-room agent invokes that environment over SSH when the code is remote. Preserve the existing artifact-only worker and external-action boundaries below.

Before any data extraction remote run:

1. `git status --short` must be clean, or the intended changes must be committed and pushed.
2. The remote repo must be updated to the pushed commit or branch before executing the job.
3. Artifact inputs may be generated locally after the code is pushed, but executable code must come from Git.
4. If the remote command fails because an artifact mode is missing, add the artifact mode locally, test it, commit, push, then retry remotely.

Remote execution is an artifact generator, not a DB worker:

- The remote worker must not read from or write to the operational DB.
- The remote worker receives file artifacts such as manifests, text files, JSON, or JSONL.
- The remote worker produces file artifacts such as extracted text, completed JSON, JSONL, reports, checksums, or logs.
- Bring the generated artifacts back with `rsync`/`scp`.
- All DB export, import, update, candidate matching, current-profile sync, and relation-table writes happen on the local/operational server.
- If a data extraction command can only run by connecting the remote worker to the operational DB, do not run it remotely. First add or use an artifact mode: local export file -> remote transform -> local import file.
- Even small remote tests follow the same boundary. For example, a 10-row test exports 10 DB rows to JSONL locally, transforms that JSONL remotely, downloads the result JSONL, then imports or verifies it locally.

Terminology rule:

- `remote worker` means `chaconne@49.247.45.243`.
- `Gemini Batch` means an external Gemini API batch job submitted from the local/operational server.
- Do not call Gemini Batch "remote execution" or "remote processing". Its request, polling, result download, ingest, and DB save are local/operational responsibilities unless the user gives fresh approval for remote credentials and external API side effects.
- `reconcile` has two separate meanings: `batch_txt_to_db --reconcile` reconciles Gemini Batch jobs locally; `remote_structured_json_classification.sh reconcile` reconciles remote worker artifacts locally. Always name the command when saying "reconcile".

Use remote execution only for local, reproducible stages unless credentials and external side effects are explicitly approved. Keep bulk outputs on the remote worker and download selected artifacts directly.

Recommended remote artifact root:

```text
~/remote-exec/artifacts/<repo>/<job-id>/
```

Record artifact paths and a compact manifest in the remote result commit or final report. Download only the needed outputs:

```bash
rsync -av --progress \
  chaconne@49.247.45.243:~/remote-exec/artifacts/exdigm/<job-id>/manifest.json \
  ./artifacts/<job-id>/
```

For directories, prefer resumable `rsync` with include/exclude filters over Git:

```bash
rsync -av --partial --progress \
  --include='*/' --include='*.json' --include='*.jsonl' --exclude='*' \
  chaconne@49.247.45.243:~/remote-exec/artifacts/exdigm/<job-id>/ \
  ./artifacts/<job-id>/
```

Safe examples:

- parser/test runs against committed fixtures
- batch prompt or schema tests
- dry-run extraction checks
- CPU-heavy local transforms
- remote generation of large intermediate files that stay outside Git
- text extraction from a manifest into text artifacts, followed by local DB import
- structured JSON search-classification enrichment from input JSONL to output JSONL, followed by local DB import

Unsafe without fresh approval:

- production Drive downloads
- Gemini Batch submission
- production DB writes
- operational DB reads for selecting work or verifying results
- credential copying

### Exdigm Artifact Patterns

For remote text extraction, the local server selects or exports the manifest, the remote worker downloads/parses files into text artifacts, and the local server imports those text artifacts into `FileStatus.extracted_text` and routing state.

For structured JSON search-classification enrichment, the local server exports rows that already have `FileStatus.structured_json` to JSONL, the remote worker runs the pure JSON transformation, and the local server imports the completed JSON back into DB.

Use the repository wrapper for long-running structured JSON search-classification enrichment jobs:

```bash
# Submit once: export local artifacts, upload them, and start the remote job in the background.
LIMIT=0 RUN_ID=json-classification-<name> scripts/remote_structured_json_classification.sh submit

# Reconcile repeatedly: poll remote state, download completed artifacts, verify checksums,
# import into local DB, and clean up the remote run dir.
scripts/remote_structured_json_classification.sh reconcile
```

`submit` must be run manually after the local code is clean, committed, and pushed. `reconcile` is the cron-safe operation and uses a lock so overlapping cron runs exit without doing duplicate work.

Keep local and remote executable paths separate. The local `UV_BIN` may be `/home/chaconne/.local/bin/uv`, while the remote worker currently resolves `uv` as `/usr/local/bin/uv`. Remote commands must use `REMOTE_UV_BIN` or `command -v uv` on the remote host; do not pass a local absolute `uv` path into the remote shell. Preflight should fail before backgrounding if the remote executable is missing.

For large imports, keep local DB pressure bounded. `remote_structured_json_classification.sh reconcile` imports completed JSONL in chunks (`IMPORT_CHUNK_SIZE`, default 500) and sleeps between chunks (`IMPORT_SLEEP_SECONDS`, default 2). Do not replace this with a one-shot import for large files unless memory, DB lock time, and rollback size have been considered.

After successful import, reconcile must clean the remote run directory. If a remote PID is still alive, terminate it only after confirming that the process command line belongs to the current run directory; never kill by stale PID alone.

Recommended structured JSON search-classification enrichment input JSONL:

```json
{"file_id":"<drive-file-id>","structured_json":{...}}
```

If completion logic needs DB-backed lookup data, export that lookup data as an artifact too. Current exdigm industry classification may use `CompanyProfile`, so pass a separate company profile JSONL instead of letting the remote worker query the operational DB:

```json
{"name":"삼성전자","name_en":"Samsung Electronics","industry":"반도체"}
```

Recommended structured JSON search-classification enrichment output JSONL:

```json
{"file_id":"<drive-file-id>","completed_structured_json":{...},"status":"ok"}
```

If a row fails, keep it as an artifact and do not hide it:

```json
{"file_id":"<drive-file-id>","status":"error","error":"<short reason>"}
```

The structured JSON search-classification enrichment remote command should call the same code path as local DB saving: `candidates.services.tagging.add_career_tags_to_extracted_json(extracted)`. Its input is an LLM structured JSON object, and its output is the completed JSON that includes `classification`, top-level `career_tags`, top-level `job_categories`, and per-career `classification`.

For checksums, create relative-path checksum files from inside the remote artifact directory:

```bash
cd "$REMOTE_DIR" && sha256sum completed.jsonl complete-report.json > checksums.sha256
```

After rsync, verify from inside the local artifact directory:

```bash
cd "$LOCAL_DIR" && sha256sum -c checksums.sha256
```

Do not create checksum manifests with remote absolute paths if they will be verified locally.

Run local Django management commands from the repository root with `uv run python manage.py ...`. Running `uv run` from an artifact directory can miss the repo virtualenv/project configuration.

If the output is large, prefer this result split:

- Git branch: code changes, prompt/schema changes, small manifests, checksums, summary reports.
- Artifact download: large extracted texts, JSONL payloads, screenshots, PDFs, DB dumps, model output batches.

## Result Intake

For a remote-source project, inspect results, run focused verification, and perform any approved Git integration over SSH in the official source checkout. Return the result report to the control room without creating a local code clone.

For the existing-local-checkout path:

1. `git fetch origin <remote-branch>`
2. Inspect commits and diff.
3. Run the narrowest local verification needed for confidence.
4. Merge, cherry-pick, or ask the user if the result includes unexpected changes.

Keep remote orchestration artifacts out of the main branch unless they are intentionally part of the task.

## Large Artifact Transfer

Use `rsync` for large outputs. It is resumable, can filter paths, and avoids bloating Git history.

Before downloading, inspect remote size:

```bash
ssh chaconne@49.247.45.243 'du -sh ~/remote-exec/artifacts/exdigm/<job-id> && find ~/remote-exec/artifacts/exdigm/<job-id> -maxdepth 2 -type f | head -50'
```

Download choices:

- one file: `scp remote:path local/path`
- resumable directory: `rsync -av --partial --progress remote:path/ local/path/`
- huge output: first download `manifest.json`, checksums, or sampled files; ask before pulling all data.

Never put downloaded bulk artifacts under tracked repo paths unless the project already expects them there. Prefer ignored local paths such as `artifacts/<job-id>/` or a user-specified data directory.

## Troubleshooting

- If SSH fails, run `ssh -T chaconne@49.247.45.243 'hostname && git --version'`.
- If GitHub fetch/push fails on remote, verify the remote worker's GitHub key and repo access.
- If the remote command leaves uncommitted changes, inspect on the remote path and commit there before pushing.
- If local worktree is dirty, commit only the intended state or use a temporary local branch.
