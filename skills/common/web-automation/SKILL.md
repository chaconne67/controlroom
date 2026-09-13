---
name: web-automation
description: Use for browser investigation, remote development UI verification, or automation involving scraping, downloads, login, form filling, posting, admin actions, Playwright, Selenium, or CDP.
---

# Web Automation

Use this skill before manipulating or extracting from a web page. Base browser behavior on the observed page and session, not guessed selectors, guessed URLs, or remembered flows.

Terminology:

- **Final-path implementation**: the durable functions, wrapper, and session service that own the browser workflow.
- **Final-path command**: the official CLI or service entry that invokes that implementation.

For remote development UI acceptance tests, first read **Remote development UI verification** below.
It defines the isolated test scope; the Operation Gate continues to govern production and external effects.

## Operation Gate

Before any browser action, declare the current phase. Declare again before changing phases.

| Phase | Purpose | Allowed path |
|---|---|---|
| **Investigation** | Observe, debug, inspect page structure, and reproduce behavior | Direct browser tools and inline inspection may create diagnostic evidence, but not the requested data, download, submission, publication, or external state |
| **Execution** | Produce requested data/downloads or persist authentication, drafts, submissions, publications, or admin state | Run the final-path command; do not substitute ad hoc browser manipulation |
| **Integration** | Convert investigation evidence into durable automation | Merge into the responsible final-path implementation stage and verify it through the final-path command |

Manual reproduction proves only observed page behavior, not the automation. If no final-path command exists, complete Integration before Execution rather than using direct manipulation as a fallback.

Execution must remain within the authority granted by the user. Stop before externally visible or destructive actions when approval is absent or ambiguous.

If the project provides a UI design skill (for example `$exdigm-design` in the Exdigm project), use it together with this one for UI or template changes. That skill owns project URLs, interaction acceptance, and screenshot verification; this skill still owns browser phase classification.

## Remote development UI verification

When the app runs on a remote server and the browser runs in the control room, follow this procedure.
Project instructions supply the SSH target, repository, runtime and start command, isolated test setup,
asset build/serve commands, target routes, and design acceptance criteria. Verify those values from the
current project before dependent actions; do not copy another project's addresses, ports, or framework settings.

### Windows actual Chrome isolation

When verification runs from a Windows control-room PC and Chrome parity matters, or the user must keep working on that PC, apply `$hidden-desktop-browser` together with this skill. The project design or domain skill remains responsible for the application context; `$hidden-desktop-browser` owns the hidden Windows desktop, actual Chrome profile, screenshots, and cleanup; this skill owns observation, step contracts, and final-path verification.

- Use the common hidden runner for browser lifecycle instead of adding a project-specific Chrome launcher or screenshot helper. For UI verification open it with `--backend playwright`: `goto` reports console errors, failed requests, and stylesheet/document responses for the navigation, `eval` measures computed styles and document overflow, and `snapshot` captures the real Chrome rendering. Use `--backend uia` only when the site rejects CDP-controlled browsers.
- Keep one hidden-browser name for the server, tunnel, role, route, and viewport being verified so evidence can be traced to that session; pass `--run-id` per verification round.
- Use the in-app browser when the user asks to see or interact with the live review. Do not treat an in-app rendering as proof of actual Chrome behavior when Chrome-specific verification is required.
- If authentication requires a visible human step, preserve the dedicated profile and request only that step. Resume the same hidden profile afterward.
- If the common runner lacks a site-independent browser operation, extend and verify the common skill first. Keep selectors, fixtures, expected UI state, and data assertions in the project domain layer.

### 1. Identify the two machines and the current session

Codex in the Windows control room operates a browser on Windows; the application and development server
run on the remote Linux host. `127.0.0.1` always refers to the machine making that connection.
A browser launched on remote Linux is a separate environment; its window is not automatically visible on Windows.
Confirm the actual execution hosts when using another agent or browser tool.

Record this once and update only changed values after a restart or tab/port change:

| Component | Evidence to retain |
|---|---|
| Server | SSH host, repository/revision or working changes, start command, process/tool session ID |
| Data | Settings, actual test DB/schema, test user role, blocked external effects |
| Connection | Server binding/port, control-room port or approved project URL, tunnel session ID |
| Browser | Machine, browser name, browser/tab IDs, exact URL |

Follow a user-specified browser. Otherwise use the hidden actual-Chrome path above when the user should not
be interrupted, and prefer an available in-app browser for a review the user should see. Inspect tool
capabilities and current tabs before selecting it. An ambient URL or an old error message is not proof that
a server, tab, or dialog is still present.

### 2. Prepare the application's real test path

Use the project's existing development/test entry point and fixtures. Confirm the actual database connection
and schema; a setting named local, development, or debug does not establish isolation. Keep credentials out
of logs. Use isolated synthetic data and existing test doubles for email, messages, and external APIs.

For UI acceptance testing, operating the actual application UI against verified isolated test data is
Investigation: it establishes application behavior, not a reusable automation's success. Assert resulting
test data as well as screen feedback. Production or external-service effects remain subject to the Operation
Gate and its final-path command requirement. Do not create an automation wrapper merely to inspect a test UI.

Check build output locations and shared mounts before building or collecting assets. Use the project's
commands and static serving configuration. A successful build does not establish that the browser received
the new CSS. Resolve manifest/hash versus source-file serving in the responsible test configuration; do not
alter production settings, inject CSS, or rewrite captured HTML to claim the actual application path passed.

### 3. Start the remote server and connect the control room

Bind the development server to the remote loopback interface and use SSH local forwarding by default.
Follow an explicitly defined project access path when one already exists; verify its server and browser
endpoints rather than silently replacing it. Check both ports and their owners before allocating a new port.

For SSH forwarding, run this command shape on the control-room machine in a tracked session.
Replace the placeholders with the verified project/session values before execution:

```text
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:<local-port>:127.0.0.1:<remote-port> <ssh-target>
```

The listener is on the control-room machine; the destination loopback is on the SSH target. The browser opens
`http://127.0.0.1:<local-port>/<route>`. If the app lives in a container, first verify the host-to-container
port mapping. Keep the server and tunnel session IDs separate even when one tool manages both.

Verify the remote process/listener and HTTP response first, then the same route from the control room.
A running SSH process alone does not prove the development server is reachable. Check redirects and the
expected application marker. Do not solve connection errors by exposing a development port publicly,
changing production firewalls/DB tunnels, or killing an unidentified process.

### 4. Verify CSS, then appearance and behavior

1. Confirm the selected tab's URL, title, logged-in role, and changed screen. A login or stale page returning
   HTTP 200 is not the requested screen.
2. Inspect the document's actual stylesheet requests, successful response/type/content, and current console
   errors. Compare representative elements' computed styles with the project's tokens/classes. Report any
   unavailable network/computed-style evidence instead of treating it as passed.
3. If assets are missing or stale, inspect the serving path, code read by the server, and cache. Fix the
   evidenced cause, refresh, and repeat the same check before judging design.
4. Inspect actual screenshots at the project's mobile and desktop widths. Check layout, typography, spacing,
   input/button positions, wrapping, and dialogs. Measure document overflow against viewport width and
   distinguish intended table scrolling from whole-page overflow.
5. Exercise affected empty, invalid, loading, success, cancellation, keyboard, and focus states as applicable.
   Submit through the actual UI in the verified test environment; check resulting data and protected records.
6. Navigate away and back through the application's partial/client navigation and repeat the affected controls.
   Attribute requests and console errors to the current attempt, distinguishing old server-shutdown errors.

Automation success without inspecting the rendered screen does not establish design accuracy. For native
alerts/confirmations, use the current tool's supported dialog API. On failure, re-observe the tab and dialog;
do not repeat an unchanged failing operation. Only when user action is necessary, give the verified browser
name, URL, current dialog text, and exact action. Tool limitations do not by themselves justify product changes.

### 5. Report and close the correct resources

Keep project test results, URL/browser/viewport, CSS application evidence, UI/data outcomes, and remaining
gaps together. Reuse this session through validation rather than repeatedly rebuilding the environment.
A fixture-owned server lives only as long as its fixture; retain it until the intended review is finished.

When showing a live review to the user, keep the server and connection alive and open the correct tab.
Verify whether the tool preserves processes after the response before promising an available URL. When
verification is finished, save evidence and stop only this run's owned tabs, server, and tunnel by tracked ID.
Preserve user/shared browsers and other jobs. Confirm cleanup of temporary fixtures, files, and test resources.

Mark stopped URLs as stopped; do not ask the user to open them or dismiss a historical dialog there. Report
code verification, a currently viewable development screen, and production deployment as separate states.

## Preflight

Before launching or attaching to a browser:

- Identify the required browser, profile, session, owner, and lifecycle: existing user browser, dedicated automation profile, transient Playwright/Selenium context, remote Linux/Xvfb Chrome, or CDP-attached Chrome.
- Determine whether the site is profile, device, 2FA, CAPTCHA, approval, or human-session bound.
- Classify the intended effect as diagnostic evidence, read-only requested output, draft-only, externally visible, or destructive.
- Identify the final-path command for Execution or declare that Integration is required first.
- Follow a user-provided browser/profile path exactly. Do not replace it with a fresh profile or another environment.
- If a required browser, profile, tool, credential, or approval is unavailable, stop and report the missing dependency instead of substituting another path.

## Investigation

Use this loop only for Investigation:

```text
Observe -> inspect structure -> map visible controls -> perform one scoped action -> verify state -> continue or stop
```

Exit Investigation when each safe-to-probe step has a verified selector/action and diagnostic postcondition, and each execution-only step has an explicit required postcondition. Do not repeat an unchanged action after the same blocker; preserve the session and evidence, then retry only when a verified premise or input has changed.

### Page Readiness

Do not treat `domcontentloaded` alone as readiness. Record the URL, title, ready state, visible text marker, viewport, and scroll height. Wait for the expected account/session marker, visible control, stable URL/title, loader completion, and required modal or frame.

### Structure Inspection

Before choosing selectors, inspect frames, shadow roots, modals, popups, virtualized lists, and rich text editor iframes.

Record each candidate frame's identity, URL, visibility, and ownership. Do not use main-DOM selectors until the target frame, modal, or popup owner is resolved.

### Control Mapping

Map visible controls before acting. Record the tag, accessible name, text, state, rectangle, form owner, and frame owner needed to distinguish each candidate. Capture evidence before safe navigation or a reversible page-state action. Map authentication or persistent-state controls, but defer their use to Execution.

Prefer human-visible controls over hidden/raw inputs:

1. Exact visible label tied to the input.
2. Visible button/control inside the correct section.
3. Coordinate click on the measured visible control.
4. Raw input click only after proving it triggers the same state.
5. Direct value assignment only after React/value tracker events are handled correctly.

### Step Contract

For every investigated step, record:

```text
precondition
selector/action
postcondition
failure evidence
```

During Investigation, perform one safe scoped action and verify URL/title/body markers, modal state, or reversible field state. Record persisted postconditions such as created/removed items, files, emails, or API responses without producing them directly; Execution verifies them through the final-path command.

Treat direct URLs and `href`s as hypotheses. For safe navigation, click the visible link once, observe behavior, compare direct navigation only after that, and preserve the click flow when JS/session state differs.

## Integration and Verification

After Investigation, stop before editing. Lock these four items:

1. Observed state and evidence.
2. Existing final-path implementation and command.
3. Exact merge point and successful behavior that must remain unchanged.
4. Verification command and expected postconditions.

Do not change a previously successful final-path stage or deployment path until its prior success contract is understood. If verification fails, return to Investigation and change the existing stage that owns the evidenced cause—such as the browser function, wrapper, or session service—instead of adding a temporary runner, bypass, or parallel workflow.

Build the durable script only after the flow is mapped. Encode:

- exact entry URL from env/config/user instruction
- browser/profile ownership and lifecycle requirements
- frame/modal resolution
- verified selectors and postconditions
- configured evidence artifacts and paths
- project-defined safety modes and approval gates
- project-approved credential inputs and redacted logs/evidence; never emit secrets, OTPs, cookies, tokens, or passwords

Verification passes only when the final-path command produces the required postconditions and evidence. Manual success, inline inspection, a temporary runner, or a separately corrected result does not pass. Follow the host project's recovery rule when verification fails; do not leave unverified integration in the final path.

Never close, kill, or delete a user-owned, shared, or persistent browser/profile, including one with an authenticated session. Close only a transient context created and owned by the current final-path run, after verification evidence is saved and no follow-up step needs the session.

## Stop Conditions

Stop and report evidence instead of continuing when:

- an externally visible or destructive action lacks clear user authority;
- the required browser, profile, tool, credential, approval, or final-path command is unavailable;
- the same blocker recurs without a changed, verified premise;
- an authentication challenge has no approved handling path;
- the requested postcondition cannot be verified.

For service-style wrappers and reusable CLI architecture, read
[service-wrapper-pattern.md](references/service-wrapper-pattern.md).
