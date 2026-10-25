# DAG Orchestrator Desktop — international launch material

**Developer:** David Pagava  
**Version:** 2.3.0  
**Project:** https://github.com/dgpdgp/dag-orchestrator-desktop  
**Download:** https://github.com/dgpdgp/dag-orchestrator-desktop/releases/tag/v2.3.0  
**Demo and verification:** https://github.com/dgpdgp/dag-orchestrator-desktop/blob/main/DEMO_RU_EN.md

> These are **draft materials**, not published posts or evidence of an endorsement. The developer should check each destination's current community rules and personally post under an account they control.

## Suggested Reddit contribution — r/ClaudeCode weekly showcase

**Suggested title:** I built a local DAG coordinator for Claude Desktop / Cowork / Claude Code

**Draft:**

I built **DAG Orchestrator Desktop v2.3.0**, a local Python MCP server and Claude plugin to coordinate coding tasks with explicit dependencies.

The idea is simple: if task A defines a contract, tasks B and C can become eligible after A finishes, while integration D waits for both. The MCP layer tracks readiness, task claims, declared file ownership, locks, retries, and recovery. The package includes a Skill and three agent roles for implementation, test verification, and review.

An important limitation: the MCP **does not launch agents or run tests** on its own. Actual parallel execution requires a Claude host that exposes subagents, and test outcomes must be verified by the executing tools.

I tested the MCP and plugin on Windows 11 and published the source, a Windows installer, standalone plugin ZIP, and a reproducible smoke-test walkthrough.

I would appreciate feedback on the dependency model, setup instructions, and whether this is useful for real multi-module projects.

GitHub: https://github.com/dgpdgp/dag-orchestrator-desktop  
Demo: https://github.com/dgpdgp/dag-orchestrator-desktop/blob/main/DEMO_RU_EN.md

— **David Pagava**

**Publishing note:** r/ClaudeCode has showcase/megathread expectations. A short promotional link drop may be removed. Prefer the current weekly showcase thread and disclose that you built the project. Do not repost repeatedly.

## Suggested short LinkedIn / X-style announcement

**DAG Orchestrator Desktop v2.3.0 is now available on GitHub.**

I created a local task-coordination plugin for Claude that uses a Python MCP server, a dependency-aware DAG workflow, and three optional specialist agent roles. It helps organize interdependent coding tasks, tracks task states and file ownership, and supports retries and recovery.

It doesn't claim to run code or launch parallel agents by itself; actual execution depends on the tools available in Claude Desktop, Cowork, or Claude Code.

Windows 11 installer, plugin ZIP, bilingual documentation, and a reproducible demo:

https://github.com/dgpdgp/dag-orchestrator-desktop

Developed by **David Pagava**. Feedback from developers is welcome.

## Hacker News — facts for a genuine, self-written Show HN

Hacker News asks authors **not to submit AI-generated post text or automated submissions**. For that reason, use the points below as background, **not as a ready-made Show HN post**:

- Project name: DAG Orchestrator Desktop (not a hosted service).
- Problem: dependent coding tasks should not start before prerequisites are finished; parallel file edits can conflict.
- Implementation: local Python 3.10+ MCP server, JSON-RPC stdio, Claude Skill, three optional agent role descriptions.
- Demo users can try: `python tools/smoke_test.py` or install the Windows package and run a trial graph in Claude.
- Distinction: scheduling/bookkeeping vs. actually launching an agent or executing tests.
- Limitations: Windows-focused installer, local Python requirement, directory approval not yet obtained, no selected code license.
- Source and steps: link GitHub repo and `DEMO_RU_EN.md`.
- Write the title and the accompanying explanation **yourself**, disclose ownership, and be present to answer technical questions.
- Official rules: https://news.ycombinator.com/showhn.html and https://news.ycombinator.com/newsguidelines.html

## Other community opportunities

- Claude plugin directory: https://claude.ai/directory/manage/new — only after eligibility, validation, and required support contact are confirmed.
- Reddit r/ClaudeAI: project showcase megathread, following the rules in force when posting.
- Technical developer communities: share the reproducible test and a real demonstration, and ask for actionable feedback rather than soliciting stars or upvotes.

## Assets to prepare before broad outreach

- [x] Public GitHub repository with visible source.
- [x] Bilingual README and v2.3.0 release description.
- [x] Two release ZIP downloads.
- [x] Reproducible DAG explanation and local MCP smoke-test instructions.
- [ ] A genuine short screen recording of Claude using `dag_*` tools and (if supported) parallel subagents.
- [ ] Decide on a license; **public source is not automatically open source**.
- [ ] Verify any community post through the developer's own account.

© 2026 David Pagava.
