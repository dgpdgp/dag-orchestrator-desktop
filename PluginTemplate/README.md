# DAG Orchestrator Desktop Plugin v2.3

**Developer:** David Pagava (Давид Пагава)  
**Copyright:** © 2026 David Pagava

Plugin candidate for Claude Cowork / Claude Code. It packages a Skill, optional agent roles and a **local Python stdio MCP** tool provider. See main `README.md` and `INSTALL_README_RU.md` in the repository.

**Requires** Python 3.10+ accessible via `python` in PATH of the plugin host. `claude-plugin/.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}`. On Windows with only `py.exe`, adjust the `command` to a Python executable that works for your session; do not assume Claude resolves `py` or runs inside the same environment as PowerShell.

**Verified scope:** The Plugin ZIP was installed in a Windows 11 Claude Desktop session, showed one Skill, one connector and three agents; a five-node agent workflow, including overlapping parallel tasks, completed. This is evidence for that installation, not a guarantee for all environments. The MCP server **does not launch subagents**, execute user code, nor verify project tests independently. It accepts agent-reported checks.
