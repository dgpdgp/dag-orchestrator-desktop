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
