# Service Wrapper Pattern

Use this reference when a web workflow is more than a one-off probe. Login, 2FA, form mapping, dry-run, publish, verify, and cleanup should be managed as one service or CLI instead of scattered temporary scripts.

This reference is language-neutral design guidance. It does not prescribe a directory layout or a mode list; each project's wrapper code is the SSOT for its own structure and modes.

When a domain-specific skill or project already declares a wrapper and final path, use that contract instead of designing a parallel wrapper from this reference.

## Wrapper Shape

A durable wrapper should provide:

- target registry when the wrapper serves multiple sites or workflows
- target-specific engines when behavior differs by site or workflow
- common browser/session manager
- common evidence writer
- common preflight/control dump
- mode-based CLI
- explicit safety gates for externally visible actions
- keep-open sessions for approval/debugging workflows

A workflow engine should expose one named step per required lifecycle stage: inspect, authenticate, navigate, prepare, commit, verify, and cleanup.

## Mode Concepts

Pick the mode set each project needs and encode it in the wrapper CLI; the wrapper's own mode list is authoritative for that project.

- `inspect`: collect DOM/iframe/modal/control dump and screenshot; no mutation except safe navigation.
- `dry-run`: fill fields only; never save/publish/submit.
- `publish`: real external action; require authority from the user and any project-defined confirmation gate.
- `test-create-delete`: with explicit authority, create a marked test artifact, verify it, delete it, and verify cleanup.
- `challenge`: preserve the browser session and evidence, then invoke the approved CAPTCHA, 2FA, or approval path; do not bypass the challenge or replace the authenticated profile.

## Keep Open

For approval/debugging flows, use a browser session that can receive follow-up commands:

1. a long-lived command loop that keeps the page object;
2. a persistent Chrome profile with fixed CDP port and session metadata;
3. Playwright `launchPersistentContext(userDataDir, ...)` when the same process will perform follow-up actions.

Never close or delete a browser/profile owned by the user, another process, or a persistent service. A wrapper may close only its own transient context after final evidence is saved and no follow-up command needs it.

## Evidence

Every non-trivial run should store a result summary, step evidence, and a final screenshot under the wrapper's configured evidence location. The result summary should include mode, URL/title, step summary, safety flags, browser ownership, and whether the session remains open.

## Probe Migration

When an exploratory script succeeds:

1. Extract verified selectors and postconditions.
2. Move them into the target workflow engine inside the wrapper.
3. Register the step/mode in the wrapper CLI.
4. Run through the wrapper, not the probe.
5. Delete the probe script and update the relevant project reference.
