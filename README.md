# DAG Orchestrator Desktop

**Версия:** 2.3.0  
**Разработчик:** **Давид Пагава / David Pagava**  
**© 2026 David Pagava**

**DAG Orchestrator Desktop** — локальная система организации сложных задач разработки в Claude Desktop, Cowork и Claude Code. Она объединяет Skill `dag-orchestrator-desktop`, MCP-сервер на Python и три роли специализированных субагентов.

> **Language:** основная документация на русском. Технические имена команд и инструментов оставлены на английском, поскольку они используются программой.

## Что умеет

- Разбивать крупную работу на этапы с зависимостями (DAG).
- Отмечать, какие этапы можно выполнять параллельно, а каким нужно дождаться предыдущих.
- Отслеживать состояние задач, выдачу заданий, блокировки, ошибки и восстановление.
- Организовывать работу Claude с тремя ролями: `dag-implementer` (разработка), `dag-test-engineer` (тестирование) и `dag-reviewer` (проверка).
- Сохранять существующие MCP-подключения Claude при установке и делать резервную копию его конфигурации.

**Важно:** сам MCP-сервер не создаёт и не запускает субагентов, не редактирует проекты и не выполняет тесты: это делает Claude при наличии соответствующих возможностей и разрешений. MCP управляет состояниями задач и зависимостями; сообщение исполнителя об успешных тестах не заменяет реальной проверки.

## Установка на Windows 11

Требуется **Python 3.10 или новее** и установленный **Claude Desktop**.

1. Скачайте **Windows Installer ZIP** со страницы [Releases](https://github.com/dgpdgp/dag-orchestrator-desktop/releases), когда релиз опубликован.
2. Распакуйте весь архив в отдельную папку, например `D:\\DAG\\INSTALL`.
3. Полностью закройте Claude Desktop (включая значок возле часов).
4. Запустите по очереди **`CHECK-FIRST.bat`**, **`INSTALL-DAG.bat`**, **`VERIFY-DAG.bat`**.
5. Запустите Claude и убедитесь, что **Настройки → Разработчик → `dag-orchestrator-desktop`** имеет статус «Выполняется / Running».
6. Для Cowork и Claude Code установите плагин из файла `DAG-Orchestrator-CLAUDE-PLUGIN-ready.zip`, который создаёт установщик: **Плагины → Добавить → Загрузить плагин**. Если плагин уже доступен в вашем аккаунте, проверьте его версию и состояние.

> Исходный отдельный ZIP плагина предназначен для ручной установки при подходящей настройке Python. Для Windows с нестандартным путём Python предпочтителен ZIP, созданный установщиком на самом компьютере.

Полная инструкция: **[INSTALLATION_GUIDE_RU.md](INSTALLATION_GUIDE_RU.md)** — в том числе разделы **4. «Что сказать Claude»** и **5. «Ежедневное использование»**.

## Как попросить Claude использовать DAG Orchestrator

Исходное имя Skill сохранено: `/dag-orchestrator-desktop` (если Claude показывает его как команду). В некоторых режимах имя команды может отображаться с префиксом плагина; также можно написать запрос обычным текстом:

```text
Используй Skill dag-orchestrator-desktop и MCP-инструменты dag_*.
Изучи проект, составь граф зависимостей задач и выдели независимые этапы.
Если среда позволяет, используй субагентов dag-implementer,
dag-test-engineer и dag-reviewer и запускай независимые работы
параллельно. Не допускай конфликтов при изменении одних файлов.
Проверяй реальные результаты тестов. В конце покажи статус задач,
проверки и оставшиеся ограничения.
```

Для мелких задач необязательно создавать DAG.

## Что находится в проекте

- `mcp/server.py` — локальный MCP-сервер.
- `PluginTemplate/` — исходники Claude Plugin (Skill, коннектор, три агента).
- `installer_engine.py`, `bootstrap.ps1`, `*.bat` — установщик и проверка.
- `tools/` — тесты установочного комплекта.
- `INSTALLATION_GUIDE_RU.md` — подробная инструкция на русском.

## Испытания и ограничения

Версия **v2.3.0** проверялась на Windows 11: установка через BAT, ответ локального MCP, отображение сервера как Running в Claude Desktop, наличие одного Skill, одного коннектора и трёх агентов. Доступность инструментов и параллельных агентов зависит от конкретной среды Claude. Проверка ZIP и тесты Python не доказывают автоматически, что подключение будет работать на любом компьютере.

Установщик не требует платного API-ключа Claude Platform сам по себе, но использование Claude и доступность функций зависят от вашего аккаунта и среды.

## Авторство и права

**Разработчик: Давид Пагава (David Pagava)**  
**© 2026 David Pagava**

Проект опубликован без выбранной лицензии. Публичный доступ к исходникам сам по себе не означает разрешения на повторное распространение или создание производных работ; условия лицензирования будут определены отдельно.

---

# English Description

**DAG Orchestrator Desktop v2.3.0**  
**Developer: David Pagava — © 2026 David Pagava**

**DAG Orchestrator Desktop** helps organize complex development tasks in Claude Desktop, Claude Cowork, and Claude Code. It combines a Claude Skill, a local Python MCP server, and three specialized subagent roles. The MCP layer coordinates a **directed acyclic graph (DAG)** of dependent tasks, tracks their states, prevents unsafe overlapping file ownership, and supports retries and recovery.

## Key features

- **Dependency-aware planning:** complete prerequisites before starting dependent tasks.
- **Parallel work when supported:** independent tasks can run concurrently if the Claude host exposes subagent execution.
- **Task-state tracking:** record task status, claims, failures, recovery, and file ownership.
- **Three agent roles:** `dag-implementer` (implementation), `dag-test-engineer` (verification), and `dag-reviewer` (review).
- **Safer Windows setup:** install, verify, back up the existing Claude Desktop configuration, and uninstall without replacing unrelated MCP entries.

The MCP server does **not** run subagents, edit project files, or independently execute build/test commands. It manages DAG state and constraints while Claude's available tools perform the work.

## Install on Windows 11

**Requirements:** Python 3.10+ and Claude Desktop.

1. Download the **Windows Installer ZIP** from the [v2.3.0 release](https://github.com/dgpdgp/dag-orchestrator-desktop/releases/tag/v2.3.0).
2. Extract the ZIP to a new folder and fully quit Claude Desktop.
3. Run `CHECK-FIRST.bat`, `INSTALL-DAG.bat`, and `VERIFY-DAG.bat` in that order.
4. Restart Claude Desktop. Under **Settings → Developer**, confirm that `dag-orchestrator-desktop` is **Running**.
5. For Cowork, upload the machine-specific `DAG-Orchestrator-CLAUDE-PLUGIN-ready.zip` created by the installer via **Plugins → Add → Upload plugin**.

The separately downloadable plugin ZIP is available for manual installation, but its Python command may not work on every Windows configuration. The installer-generated ZIP is preferable on machines with a custom Python path.

## How to use the plugin

The original Skill name remains `dag-orchestrator-desktop`. Where the interface supports it, select `/dag-orchestrator-desktop`; some Claude surfaces show namespaced commands instead.

Example request to Claude:

```text
Use the dag-orchestrator-desktop Skill and the available dag_* MCP tools.
Inspect my project and create a dependency-aware DAG plan.
Delegate independent steps to dag-implementer, dag-test-engineer,
and dag-reviewer when subagents are supported. Avoid overlapping edits
to the same files. Run actual tests and report confirmed results,
unfinished tasks, and any limitations.
```

For small tasks, there is no need to create a DAG.

The complete [Russian installation guide](INSTALLATION_GUIDE_RU.md) includes **Section 4 (What to tell Claude)** and **Section 5 (Daily use)**.

## Release files

- [Windows Installer ZIP](https://github.com/dgpdgp/dag-orchestrator-desktop/releases/download/v2.3.0/DAG-Orchestrator-Windows-Installer-v2.3.0-David-Pagava.zip)
- [Standalone Claude Plugin ZIP](https://github.com/dgpdgp/dag-orchestrator-desktop/releases/download/v2.3.0/DAG-Orchestrator-CLAUDE-PLUGIN-v2.3.0-David-Pagava.zip)

**Notes:** Windows 11 has been tested for core installation and MCP startup, but functionality depends on Claude version, Python availability, and account permissions. The installer is not digitally signed. No reuse or redistribution license has been selected yet.

**Developed by David Pagava.**
