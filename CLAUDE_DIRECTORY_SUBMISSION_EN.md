# Claude Plugin Directory — submission draft (not submitted)

**Plugin:** DAG Orchestrator Desktop  
**Version:** 2.3.0  
**Developer:** David Pagava (Давид Пагава)  
**Source:** https://github.com/dgpdgp/dag-orchestrator-desktop  
**Plugin directory within the source repository:** [PluginTemplate](https://github.com/dgpdgp/dag-orchestrator-desktop/tree/main/PluginTemplate)  
**Stable released archives:** https://github.com/dgpdgp/dag-orchestrator-desktop/releases/tag/v2.3.0  
**Skill name:** `dag-orchestrator-desktop` — do not rename.

## Listing title

DAG Orchestrator Desktop

## Short English summary

Coordinate complex Claude development tasks with a local, dependency-aware DAG MCP server, a Skill, and optional specialized subagents.

## Full English description

DAG Orchestrator Desktop helps Claude structure larger software-development jobs into a dependency graph. Its Python-based local MCP server records task states, checks prerequisites, coordinates task claims, enforces declared file ownership and resource locks, and supports retries and recovery. A bundled Skill describes a safe workflow for integrating and reviewing complex changes. Three optional specialized roles assist with implementation, test verification, and read-only review.

The tool is designed for Claude Desktop, Cowork, and Claude Code on supported Windows setups. Parallel agents run **only** when the Claude host provides actual subagent capabilities. The local MCP server **does not** launch agents, edit source files, execute test commands, or independently verify agent-reported checks. Users retain control over file edits and approvals.

### Who it is for

Developers working on multi-module applications, refactoring, debugging, or coordination of interdependent coding tasks.

### Three supported example prompts

1. **Build a multi-module web app:** "Use dag-orchestrator-desktop to define an API contract, delegate independent frontend and backend tasks, gate integration on both tasks, and require a final regression-test report."
2. **Refactor safely:** "Use the Skill and available dag_* tools to plan a refactor across independent modules, isolate file ownership, run the real existing tests, and report what remains unverified."
3. **Debug and review:** "Create a graph for reproducing a bug, implementing a fix, verifying tests, and conducting independent read-only review. Do not mark work complete unless the checks genuinely ran."

### Core capabilities

- Dependency graphs and task readiness checks.
- File ownership and resource-lock conflict awareness.
- Task claiming and state tracking, with retries and recovery.
- Optional agent role guidance for implementation, testing, and review.
- Local Windows installer with backup of existing Claude Desktop MCP configuration.

### Technical integration

- Type: **Plugin bundle** with a local Python stdio MCP, an Agent Skill, and agent descriptions.
- Python: 3.10 or later; uses Python standard library.
- Plugin manifest: `PluginTemplate/.claude-plugin/plugin.json`.
- Plugin MCP config: `PluginTemplate/.mcp.json`.
- Plugin skill: `PluginTemplate/skills/dag-orchestrator-desktop/SKILL.md`.
- Requires a locally executable Python interpreter visible to the Claude plugin host. The standalone MCP in Desktop Chat must be configured separately by the installer; availability in Chat does not imply the MCP is available in Cowork.
- State is stored in the user's local `~/.dag-orchestrator-desktop/state` directory by default. Users must not place credentials or other sensitive information inside task descriptions or summaries.

### Support & docs

- Documentation: https://github.com/dgpdgp/dag-orchestrator-desktop/blob/main/README.md
- Demonstration: https://github.com/dgpdgp/dag-orchestrator-desktop/blob/main/DEMO_RU_EN.md
- Troubleshooting: https://github.com/dgpdgp/dag-orchestrator-desktop/blob/main/INSTALLATION_GUIDE_RU.md
- Issue reporting: https://github.com/dgpdgp/dag-orchestrator-desktop/issues
- Release ZIPs: https://github.com/dgpdgp/dag-orchestrator-desktop/releases/tag/v2.3.0

## Before submitting — unresolved requirements

**Not ready to claim directory approval or a completed application.** The following require the developer's review and/or Anthropic's validator feedback:

1. **Submission access:** verify the eligible paid Claude developer account can sign in to the submission portal. The browser login and submission confirmation must be completed in the developer's account.
2. **Plugin source selection:** the root of this repository is the Windows installer, not the plugin manifest. The plugin package is in `PluginTemplate/`. Confirm the portal accepts a subdirectory source; if not, restructure only the submission representation **without changing the released v2.3.0 installer/MCP**.
3. **Host compatibility:** the plugin's `.mcp.json` invokes `python`. Confirm the directory validator supports local Python stdio MCP and that expected user environments can find Python. Avoid describing the plugin as one-click installable across all systems without evidence.
4. **Developer contact:** Anthropic's Directory Policy requests verified developer contact/support details. Use a real address or other verified contact supplied by David Pagava; do not invent one. GitHub Issues can be used as a public support channel but does not itself prove verified contact.
5. **Testing provision:** provide the reviewer a reproducible local test workflow, an example graph, and any testing account/sample data required by the portal. No third-party sign-in account is required by this local MCP, but Anthropic's policy may still request test access.
6. **Privacy and security:** review data storage, permissions, tool descriptions and data handling against Anthropic's current Directory Policy. Provide a privacy notice if the portal determines one is needed. Never publish local tokens, MCP configs with secrets, or user DAG state.
7. **Licensing:** no license has been selected for this public source repository. Decide explicitly how users may copy, modify, and redistribute it before marketing it as open source. Do **not** add a license without the author's approval.
8. **Visuals and screenshots:** do not present an illustrative graph as a recorded live parallel run. Real demos must show actual observed Claude tool calls.

### Official sources

- [Anthropic: Build plugins for Claude](https://claude.com/resources/articles/build-plugins-for-claude)
- [Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy)
- [Anthropic community plugin marketplace](https://github.com/anthropics/claude-plugins-community)
- [Claude developer submission portal](https://claude.ai/directory/manage/new) — may require login and an eligible plan. Portal navigation can change.

**Status:** submission copy prepared; **not submitted, not under review, not approved or listed**.

© 2026 David Pagava.
