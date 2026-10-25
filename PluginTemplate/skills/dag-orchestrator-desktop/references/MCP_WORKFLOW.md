> IMPORTANT (v2.3): Standalone Chat MCP configuration is not shared with Cowork. A plugin-bundled local MCP may be available in Cowork/Claude Code when the host exposes it. Verify instead of assuming.

# MCP workflow reference (DAG Orchestrator Desktop 2.3)

**Tools perform only bookkeeping.** They do not spawn subprocesses/subagents, edit source code or verify tests.

Example calls (tool names below refer to tools surfaced by your MCP connector, not shell commands):

1. `dag_create({"graph_id":"sample_portal_01","title":"Портал", "tasks":[...]})` — once; fails if ID exists.
2. `dag_ready({"graph_id":"sample_portal_01"})` — list *individually claimable* tasks; this is NOT necessarily a mutually independent batch.
3. `dag_parallel_batch({"graph_id":"sample_portal_01"})` — obtain a pairwise nonconflicting snapshot before parallel launch; every task must still be claimed atomically.
3. `dag_claim({"graph_id":"sample_portal_01","task_id":"contracts","worker":"agent-interfaces","lease_seconds":3600})` — returns private token and **direct parent** outputs.
4. Work and verify using actual Cowork/subagent capabilities. Claim and spawn are separate operations.
5. `dag_complete({"graph_id":"sample_portal_01","task_id":"contracts","claim_token":"<return token>","output_summary":"contract created; lint passed","checks_passed":true,"artifacts":["docs/api-contract.md"]})`.
6. Or `dag_fail(..., "error":"API test returned failure")`, then fix and claim again if requeued.
7. After interruption `dag_status` and, after expiry only, `dag_recover`; **always inspect partial file edits**.
8. `dag_pause` toggles new claims. `dag_retry_failed` manually resets a permanently failed task **only after root cause resolution**.

Status per task is one of `pending`, `in_progress`, `completed`, `failed`. `blocked_by` is derived from parents and doesn't create a fifth stored status.

### Critical details

- Claims have expiring leases; renew while active. If the lease expires, completion is rejected until recovery and re-claim.
- `max_retries` (0–3) means extra attempts **after** initial attempt. Permanent failure blocks descendants.
- The server prevents concurrent claims to the same declared `owned_files` or `locks`. It **cannot** prevent unrelated external processes from modifying those files. Declare ownership accurately.
- `output_summary` is limited to 4000 characters. Do not put secrets or personal data there.
- `dag_complete(checks_passed=true)` is a declaration **by the agent**; the server never runs tests.
- State persists locally in `~/.dag-orchestrator-desktop/state` by default, independent of the Claude chat and Cowork cloud workspace.

### v2.3 reliability notes

- `dag_status` deliberately omits output summaries, artifacts, worker IDs, claim tokens, completion receipts and free-form errors. `dag_claim` grants direct parent summaries; this is data minimization, not authenticated access control.
- An identical `dag_complete` with the same original claim token, report and `checks_passed=true` returns `replayed=true`, with no revision change. Conflicting replays are rejected.
- Files named like Windows devices (`CON`, `NUL.txt`, `COM1`), invalid Windows characters and duplicates after path normalization are refused. Coarse ownership locks permit `*` or `path/*`.
- Each overwritten graph JSON retains one previous snapshot as `graph.json.bak`. A corrupted current state does not auto-restore from the backup because that could silently lose an acknowledged completion.
