# DAG Orchestrator Desktop v2.3.0

**Разработчик: Давид Пагава / David Pagava**  
**© 2026 David Pagava**

Первый публичный выпуск DAG Orchestrator Desktop для Claude Desktop / Cowork / Claude Code на Windows 11.

## Что входит в релиз

- **DAG-Orchestrator-Windows-Installer-v2.3.0-David-Pagava.zip** — установщик для Windows 11 с проверкой Python, сохранением конфигурации Claude, резервной копией и проверкой работы локального MCP.
- **DAG-Orchestrator-CLAUDE-PLUGIN-v2.3.0-David-Pagava.zip** — отдельный ZIP Claude Plugin (Skill, MCP и три специализированных агента).
- Исходный код, тесты, примеры и русская документация — в репозитории.

## Установка

1. Установите Python 3.10+ и Claude Desktop.
2. Распакуйте Windows Installer ZIP в отдельную папку.
3. Закройте Claude Desktop полностью.
4. Запустите по очереди **CHECK-FIRST.bat**, **INSTALL-DAG.bat**, **VERIFY-DAG.bat**.
5. Проверьте в Claude Desktop → Настройки → Разработчик, что сервер `dag-orchestrator-desktop` выполняется.
6. Для Cowork загрузите ZIP плагина, созданный установщиком для вашего компьютера: `DAG-Orchestrator-CLAUDE-PLUGIN-ready.zip`.

Подробнее: [Инструкция по установке и использованию](https://github.com/dgpdgp/dag-orchestrator-desktop/blob/main/INSTALLATION_GUIDE_RU.md), включая разделы 4 (готовый запрос Claude) и 5 (ежедневное использование).

**Команда Skill сохранена:** `/dag-orchestrator-desktop` там, где поддерживается интерфейсом; переименование в `/dag` не выполнялось.

## Проверенные условия

Основные сценарии установки и MCP проверялись на Windows 11; поведение зависит от версии Claude Desktop, доступа к локальному Python и разрешений аккаунта. MCP управляет DAG-состояниями и зависимостями, но не выполняет работу субагентов самостоятельно.

## Примечание

Программные файлы этой версии не изменялись ради публикации; сведения об авторе и документация добавлены отдельно. ZIP-установщик не подписан сертификатом Authenticode. Лицензия на использование и переработку исходного кода пока не выбрана.

---

# English — DAG Orchestrator Desktop v2.3.0

**Developer: David Pagava**  
**© 2026 David Pagava**

The first public release of **DAG Orchestrator Desktop**, a local task-orchestration system for development workflows in **Claude Desktop, Claude Cowork, and Claude Code** on Windows 11.

## What it does

The project combines a Claude Skill, a Python-based MCP server, and three specialized subagent roles to help Claude organize larger development tasks as a **directed acyclic graph (DAG)**. It tracks task dependencies, status, claims, file ownership, retries, and recovery. Independent tasks may be handled in parallel when the Claude environment supports subagents.

Included roles:

- `dag-implementer` — implements an assigned task.
- `dag-test-engineer` — independently checks builds, tests, and acceptance criteria.
- `dag-reviewer` — reviews changes and risks.

**Important:** the MCP server coordinates task state and dependencies; it does **not** launch subagents, write code, or execute tests by itself. Those actions require the appropriate Claude tools and permissions. A reported test result is not a substitute for actually running the tests.

## Downloads

- **`DAG-Orchestrator-Windows-Installer-v2.3.0-David-Pagava.zip`** — Windows 11 installer package, including Python and configuration checks, MCP setup, backup of the existing Claude configuration, verification, and uninstall scripts.
- **`DAG-Orchestrator-CLAUDE-PLUGIN-v2.3.0-David-Pagava.zip`** — standalone Claude Plugin package containing the Skill, MCP connector, and three agent definitions.

## Installation on Windows 11

1. Install **Python 3.10+** and **Claude Desktop**.
2. Extract the **Windows Installer ZIP** to a separate folder.
3. Quit Claude Desktop completely.
4. Run **`CHECK-FIRST.bat`**, then **`INSTALL-DAG.bat`**, then **`VERIFY-DAG.bat`**.
5. Reopen Claude Desktop and verify that `dag-orchestrator-desktop` shows **Running** under **Settings → Developer**.
6. For Claude Cowork, upload the machine-specific `DAG-Orchestrator-CLAUDE-PLUGIN-ready.zip` produced by the installer via **Plugins → Add → Upload plugin**. The standalone downloadable ZIP may require adjustment if Python is installed at a different location.

## Using the Skill

The original Skill name remains **`dag-orchestrator-desktop`**. Where available, select **`/dag-orchestrator-desktop`** in Claude; in some interfaces plugin commands may be namespaced. You can also ask Claude:

> Use the `dag-orchestrator-desktop` Skill and available `dag_*` MCP tools. Review my project, create a dependency-aware DAG plan, delegate independent tasks to the implementer, test engineer, and reviewer where supported, avoid concurrent edits to the same files, run real checks, and report completed and outstanding work.

See the full [Russian installation and usage guide](https://github.com/dgpdgp/dag-orchestrator-desktop/blob/main/INSTALLATION_GUIDE_RU.md), including sections 4 and 5 for prompts and everyday use.

## Compatibility and limitations

Windows 11 and the local MCP workflow have been tested, but compatibility with every Python installation or Claude environment is not guaranteed. Access to subagents and MCP integrations depends on the installed version, account permissions, and runtime environment. The ZIP installer is **not digitally signed**. No open-source license has been selected yet; public availability does not automatically grant reuse rights.

**Developed by David Pagava.**
