# Remote Execution Policy

Use `chaconne@49.247.45.243` as a compute worker, not as a source of truth. Git is for source state and small review artifacts; `rsync`/`scp` is for large generated outputs.

## Allowed By Default

- Running tests, linters, static checks, and browser/screenshot verification.
- Running code generation or implementation agents when all inputs are committed.
- Running local-only data processing against committed fixtures or safe test data.
- Producing Git commits on a dedicated result branch.
- Storing large generated artifacts outside Git under `~/remote-exec/artifacts/...`.
- Downloading selected artifacts with `rsync` after inspecting size and manifest.

## Requires Explicit Approval

- Copying `.env`, service-account JSON, API tokens, SSH keys, database dumps, or private credentials.
- Accessing Google Drive, Gemini Batch, Telegram, production databases, paid APIs, or user-owned external systems from the remote server.
- Deploying or restarting production services.
- Pushing directly to `main`.
- Committing large generated extraction outputs to Git.

## Local Intake Checklist

Before applying remote results locally:

1. Fetch the result branch.
2. Inspect commits and diff.
3. Confirm no secrets or orchestration junk were committed.
4. Run focused local checks.
5. Merge or cherry-pick only after review.

For large artifacts:

1. Inspect remote `du -sh` and manifest first.
2. Download only required files with `rsync --partial --progress`.
3. Keep bulk outputs in ignored local artifact/data paths.
4. Do not add artifacts to Git unless explicitly requested.
