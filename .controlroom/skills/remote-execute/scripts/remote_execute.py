#!/usr/bin/env python3
"""Run a committed repo task on the remote worker and push result commits."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


DEFAULT_REMOTE = "chaconne@49.247.45.243"
DEFAULT_REMOTE_ROOT = "~/remote-exec"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, check=check)


def out(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower()
    return value[:48] or "job"


def shell_single_quote(value: str) -> str:
    return shlex.quote(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--remote-name", default="origin")
    parser.add_argument("--branch")
    parser.add_argument("--job-name", default="job")
    parser.add_argument("--command", required=True)
    parser.add_argument("--keep-remote", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    inside = out(["git", "rev-parse", "--show-toplevel"], repo)
    repo = Path(inside)

    status = out(["git", "status", "--short"], repo)
    if status:
        print("Local worktree is dirty. Commit or exclude changes before remote execution.", file=sys.stderr)
        print(status, file=sys.stderr)
        return 2

    remote_url = out(["git", "remote", "get-url", args.remote_name], repo)
    head = out(["git", "rev-parse", "HEAD"], repo)
    current_branch = out(["git", "branch", "--show-current"], repo) or "detached"
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = args.branch or f"remote-exec/{stamp}-{slugify(args.job_name)}"
    remote_dir = f"{args.remote_root.rstrip('/')}/{slugify(Path(remote_url).stem)}/{slugify(branch)}"

    run(["git", "push", args.remote_name, f"{head}:refs/heads/{branch}"], repo)

    remote_script = f"""
set -euo pipefail
REPO_URL={shell_single_quote(remote_url)}
BRANCH={shell_single_quote(branch)}
REMOTE_DIR={shell_single_quote(remote_dir)}
COMMAND={shell_single_quote(args.command)}
mkdir -p "$(dirname "$REMOTE_DIR")"
if [ ! -d "$REMOTE_DIR/.git" ]; then
  git clone "$REPO_URL" "$REMOTE_DIR"
fi
cd "$REMOTE_DIR"
git fetch origin "$BRANCH"
git checkout -B "$BRANCH" "origin/$BRANCH"
eval "$COMMAND"
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Remote command left uncommitted changes:" >&2
  git status --short >&2
  exit 3
fi
git push origin "HEAD:$BRANCH"
echo "REMOTE_BRANCH=$BRANCH"
echo "REMOTE_DIR=$REMOTE_DIR"
"""

    run(["ssh", args.remote, "bash", "-lc", remote_script])

    run(["git", "fetch", args.remote_name, branch], repo)
    print()
    print("Remote execution finished.")
    print(f"Base branch: {current_branch}")
    print(f"Remote result branch: {branch}")
    print()
    print("Inspect locally:")
    print(f"  git log --oneline HEAD..{args.remote_name}/{branch}")
    print(f"  git diff HEAD..{args.remote_name}/{branch}")
    print()
    print("Apply when ready:")
    print(f"  git merge --ff-only {args.remote_name}/{branch}")
    if not args.keep_remote:
        print()
        print("Optional cleanup after merge:")
        print(f"  git push {args.remote_name} --delete {branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
