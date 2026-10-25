#!/usr/bin/env python3
"""DAG Orchestrator Windows installer: stdlib-only, no elevation, transactional.

The user must install the Claude account plugin through Claude's UI.
The installer modifies exactly one selected Claude Desktop Chat MCP JSON entry.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

NAME = 'dag-orchestrator-desktop'
VERSION = '2.3.0'
ROOT = Path(__file__).resolve().parent
SERVER = ROOT / 'mcp' / 'server.py'
TEMPLATE = ROOT / 'PluginTemplate'
PLUGIN_FILE = 'DAG-Orchestrator-CLAUDE-PLUGIN-ready.zip'

class InstallerError(Exception):
    pass


def say(message):
    print(message, flush=True)


def checked_python() -> Path:
    if sys.version_info < (3, 10):
        raise InstallerError('Нужен Python 3.10 или новее.')
    python = Path(sys.executable).resolve()
    if not python.is_file():
        raise InstallerError('Не найден исполняемый файл Python.')
    return python


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise InstallerError(f'Нет конфигурации Claude: {path}. Запустите Claude Desktop хотя бы один раз.')
    def no_duplicates(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f'Повторяющийся ключ JSON: {key}')
            obj[key] = value
        return obj
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=no_duplicates)
    except (UnicodeError, OSError, ValueError) as ex:
        raise InstallerError('Файл Claude config имеет некорректный JSON. Запись отменена: ' + str(ex)) from ex
    if not isinstance(data, dict):
        raise InstallerError('Файл Claude config должен содержать JSON-объект.')
    servers = data.get('mcpServers', {})
    if not isinstance(servers, dict):
        raise InstallerError('Значение mcpServers должно быть JSON-объектом.')
    return data


def get_appx_families():
    """Read installed package identity; do not guess from stale package directories."""
    if os.name != 'nt':
        return []
    script = "Get-AppxPackage -Name Claude | Select-Object -ExpandProperty PackageFamilyName"
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return sorted(set(x.strip() for x in result.stdout.splitlines() if x.strip().startswith('Claude_')))


def discover_config(appdata: Path, localappdata: Path, families=None):
    """MSIX config is selected by active installed package, not similar stale folders."""
    families = get_appx_families() if families is None else families
    if len(families) > 1:
        raise InstallerError('Найдено несколько установленных пакетов Claude. Нельзя безопасно выбрать конфигурацию автоматически.')
    if len(families) == 1:
        family = families[0]
        path = localappdata / 'Packages' / family / 'LocalCache' / 'Roaming' / 'Claude' / 'claude_desktop_config.json'
        if not path.is_file():
            raise InstallerError('Claude Microsoft Store установлен, но его конфигурация пока не создана. Запустите Claude Desktop, войдите в аккаунт и повторите.')
        return path, 'Microsoft Store / MSIX'
    # If the AppX query was unavailable, refuse to guess among multiple candidates.
    candidates = sorted((localappdata / 'Packages').glob('Claude_*/LocalCache/Roaming/Claude/claude_desktop_config.json'))
    if len(candidates) > 1:
        raise InstallerError('Обнаружено несколько MSIX-конфигураций Claude, активная не определена. Установка остановлена без изменений.')
    if len(candidates) == 1:
        return candidates[0], 'MSIX (по существующей конфигурации)'
    path = appdata / 'Claude' / 'claude_desktop_config.json'
    if not path.is_file():
        raise InstallerError('Конфигурация Claude не найдена. Сначала установите и один раз запустите Claude Desktop.')
    return path, 'Classic'


def verify_manifest():
    file = ROOT / 'payload-manifest.json'
    if not file.is_file():
        raise InstallerError('В установочном комплекте отсутствует payload-manifest.json.')
    doc = json.loads(file.read_text('utf-8'))
    if doc.get('version') != VERSION or not isinstance(doc.get('sha256'), dict):
        raise InstallerError('Некорректный manifest установочного комплекта.')
    for rel, digest in doc['sha256'].items():
        path = ROOT.joinpath(*rel.split('/'))
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise InstallerError(f'Отсутствует или повреждён файл установочного комплекта: {rel}')
    return len(doc['sha256'])


def run_smoke(server: Path, python: Path):
    """MCP initialize / tools/list / create / ready in an isolated disposable state."""
    lines = [
        {'jsonrpc':'2.0', 'id':1, 'method':'initialize', 'params':{
            'protocolVersion':'2025-06-18', 'capabilities':{},
            'clientInfo':{'name':'dag-installer-selftest', 'version':'1'}}},
        {'jsonrpc':'2.0', 'method':'notifications/initialized'},
        {'jsonrpc':'2.0', 'id':2, 'method':'tools/list'},
        {'jsonrpc':'2.0', 'id':3, 'method':'tools/call', 'params':{'name':'dag_create', 'arguments':{
            'graph_id':'installer_smoke', 'title':'Temporary installer smoke',
            'tasks':[{'id':'A','title':'Predecessor'}, {'id':'B','title':'Successor','depends_on':['A']}]
        }}},
        {'jsonrpc':'2.0', 'id':4, 'method':'tools/call', 'params':{
            'name':'dag_ready', 'arguments':{'graph_id':'installer_smoke'}}}
    ]
    with tempfile.TemporaryDirectory(prefix='dag-install-smoke-') as temp:
        env = dict(os.environ, DAG_STATE_DIR=temp)
        try:
            proc = subprocess.run([str(python), '-B', str(server)],
                    input='\n'.join(json.dumps(x) for x in lines) + '\n',
                    capture_output=True, text=True, timeout=25, env=env)
        except (OSError, subprocess.TimeoutExpired) as ex:
            raise InstallerError('MCP smoke-test не смог запустить сервер: ' + str(ex)) from ex
        if proc.returncode:
            raise InstallerError('MCP-сервер завершился с ошибкой при проверке: ' + proc.stderr[-400:])
        try:
            responses = [json.loads(x) for x in proc.stdout.splitlines() if x.strip()]
            if len(responses) != 4 or len(responses[1]['result']['tools']) < 10:
                raise ValueError('Некорректный tools/list или число ответов.')
            if responses[2]['result'].get('isError', False):
                raise ValueError('dag_create вернул isError.')
            ready = json.loads(responses[3]['result']['content'][0]['text'])['ready']
            if [x['id'] for x in ready] != ['A']:
                raise ValueError('DAG зависимости выполняются неверно.')
            if not (Path(temp) / 'installer_smoke.json').is_file():
                raise ValueError('MCP не сохранил состояние.')
        except (ValueError, IndexError, KeyError, TypeError) as ex:
            raise InstallerError('Ошибка протокола MCP: ' + str(ex)) from ex
    return True


def timestamp():
    return datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + uuid.uuid4().hex[:6]


def atomic_write(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.new-' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(temp), str(path))
    finally:
        if temp.exists():
            temp.unlink()


def make_plugin_zip(destination: Path, python: Path):
    if not (TEMPLATE / '.claude-plugin' / 'plugin.json').is_file():
        raise InstallerError('Не найдена структура PluginTemplate/.claude-plugin.')
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=8) as out:
        for file in sorted(TEMPLATE.rglob('*')):
            if not file.is_file():
                continue
            if file.is_symlink():
                raise InstallerError('Символические ссылки запрещены в шаблоне плагина.')
            rel = file.relative_to(TEMPLATE).as_posix()
            if rel == '.mcp.json':
                config = json.loads(file.read_text('utf-8'))
                config['mcpServers'][NAME]['command'] = str(python)
                body = (json.dumps(config, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                out.writestr(rel, body)
            else:
                out.write(file, rel)
    validate_plugin_zip(destination, python)


def validate_plugin_zip(archive: Path, python: Path):
    mandatory = {'.claude-plugin/plugin.json','.mcp.json','mcp/server.py',
                 'skills/dag-orchestrator-desktop/SKILL.md',
                 'agents/dag-implementer.md','agents/dag-test-engineer.md','agents/dag-reviewer.md'}
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise InstallerError('ZIP плагина повреждён.')
        names = z.namelist()
        if any('\\' in x or x.startswith('/') or '..' in x.split('/') for x in names):
            raise InstallerError('ZIP плагина имеет недопустимые пути.')
        if not mandatory.issubset(set(names)):
            raise InstallerError('ZIP плагина содержит не все необходимые файлы.')
        config = json.loads(z.read('.mcp.json'))
        if config['mcpServers'][NAME]['command'] != str(python):
            raise InstallerError('Python путь не прописан в ZIP плагина.')


def is_our_entry(entry, destination: Path):
    if not isinstance(entry, dict) or not isinstance(entry.get('args'), list):
        return False
    expected = str(destination / 'server.py')
    return any(isinstance(x, str) and x.casefold() == expected.casefold() for x in entry['args'])


def write_config(original: dict, path: Path, python: Path, destination: Path):
    modified = copy.deepcopy(original)
    servers = modified.setdefault('mcpServers', {})
    if not isinstance(servers, dict):
        raise InstallerError('Значение mcpServers должно быть объектом.')
    existing = servers.get(NAME)
    if existing is not None and not is_our_entry(existing, destination):
        raise InstallerError(f'Запись {NAME} указывает на чужую установку. Изменения отменены.')
    servers[NAME] = {'command': str(python), 'args': [str(destination / 'server.py')]}
    encoded = (json.dumps(modified, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    backup = path.with_name(path.name + '.backup-DAG-' + timestamp())
    shutil.copy2(path, backup)
    try:
        atomic_write(path, encoded)
    except BaseException:
        atomic_write(path, backup.read_bytes())
        raise
    return backup


def install(config_path: Path, dest: Path, python: Path, source_dir: Path | None = None, publish_local_copy=True):
    """Transaction: stage and verify copies, then change config with a backup."""
    source = source_dir or ROOT
    doc = load_json(config_path)
    if doc.get('mcpServers', {}).get(NAME) is not None and not is_our_entry(doc['mcpServers'][NAME], dest):
        raise InstallerError('Имеется чужая запись DAG с тем же именем. Не перезаписываем.')
    dest.mkdir(parents=True, exist_ok=True)
    installed = dest / 'server.py'
    old_server = installed.read_bytes() if installed.exists() else None
    plugin = dest / PLUGIN_FILE
    old_plugin = plugin.read_bytes() if plugin.exists() else None
    try:
        atomic_write(installed, (source / 'mcp' / 'server.py').read_bytes())
        run_smoke(installed, python)
        tmpzip = dest / ('plugin-new-' + uuid.uuid4().hex + '.zip')
        try:
            make_plugin_zip(tmpzip, python)
            os.replace(str(tmpzip), str(plugin))
        finally:
            if tmpzip.exists(): tmpzip.unlink()
        backup = write_config(doc, config_path, python, dest)
    except BaseException:
        if old_server is None:
            if installed.exists(): installed.unlink()
        else:
            atomic_write(installed, old_server)
        if old_plugin is None:
            if plugin.exists(): plugin.unlink()
        else:
            atomic_write(plugin, old_plugin)
        raise
    # Optional user-facing copy; can fail in protected extraction folders.
    local_copy = source / PLUGIN_FILE
    if publish_local_copy:
        try:
            shutil.copy2(plugin, local_copy)
            local_copy_msg = str(local_copy)
        except OSError:
            local_copy_msg = f'невозможна запись в папку распаковки, ZIP доступен здесь: {plugin}'
    else:
        local_copy_msg = str(plugin)
    return {'config':str(config_path),'backup':str(backup),'server':str(installed),
            'plugin':str(plugin),'plugin_local':local_copy_msg}


def verify(config_path: Path, dest: Path, python: Path):
    doc = load_json(config_path)
    entry = doc.get('mcpServers', {}).get(NAME)
    if not is_our_entry(entry, dest):
        raise InstallerError('Запись DAG отсутствует либо указывает на другую установку.')
    server = dest / 'server.py'
    if not server.is_file():
        raise InstallerError(f'Отсутствует установленный server.py: {server}')
    if not (dest / PLUGIN_FILE).is_file():
        raise InstallerError('Отсутствует ZIP плагина. Повторите установку.')
    configured_python = Path(entry['command'])
    if not configured_python.is_file():
        raise InstallerError(f'Python в конфигурации не найден: {configured_python}')
    run_smoke(server, configured_python)
    validate_plugin_zip(dest / PLUGIN_FILE, configured_python)
    return len(doc.get('mcpServers', {}))


def uninstall(config_path: Path, dest: Path):
    doc = load_json(config_path)
    servers = doc.get('mcpServers', {})
    entry = servers.get(NAME)
    if entry is None:
        return None
    if not is_our_entry(entry, dest):
        raise InstallerError('В конфигурации установлен другой DAG MCP. Удаление отменено.')
    new = copy.deepcopy(doc)
    del new['mcpServers'][NAME]
    backup = config_path.with_name(config_path.name + '.backup-DAG-uninstall-' + timestamp())
    shutil.copy2(config_path, backup)
    try:
        atomic_write(config_path, (json.dumps(new, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    except BaseException:
        atomic_write(config_path, backup.read_bytes())
        raise
    # Intentionally keep local files and DAG state for rollback and plugin reuse.
    return backup


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['install','verify','uninstall','check'])
    args = parser.parse_args(argv)
    if os.name != 'nt':
        raise InstallerError('Установщик предназначен для Windows 10/11. Другие ОС проверяются только тестами.')
    python = checked_python()
    local = os.environ.get('LOCALAPPDATA')
    roam = os.environ.get('APPDATA')
    if not local or not roam:
        raise InstallerError('Не найдены APPDATA или LOCALAPPDATA. Запустите без повышения прав от имени своего пользователя.')
    config_path, kind = discover_config(Path(roam), Path(local))
    dest = Path(local) / 'DAGOrchestratorDesktop'
    count = verify_manifest() if args.action in ('check', 'install') else 0
    say(f'DAG Orchestrator Desktop v{VERSION}')
    say('Python: ' + str(python))
    say('Claude: ' + kind)
    say('Конфигурация: ' + str(config_path))
    if count:
        say(f'Проверена целостность комплекта: {count} файлов.')
    if args.action == 'check':
        load_json(config_path)
        run_smoke(SERVER, python)
        say('CHECK OK: файлы, Python, Claude config и MCP проверены. Изменений нет.')
    elif args.action == 'install':
        run_smoke(SERVER, python)
        result = install(config_path, dest, python)
        say('INSTALL OK: MCP добавлен/обновлён с сохранением существующих настроек.')
        say('Резервная копия: ' + result['backup'])
        say('Установленный сервер: ' + result['server'])
        say('Плагин Cowork ZIP: ' + result['plugin_local'])
        say('ВНИМАНИЕ: Plugin устанавливается вручную через Claude > Plugins > Загрузить плагин.')
        say('Перезапустите Claude Desktop полностью (Выход/Quit, затем запуск).')
    elif args.action == 'verify':
        count = verify(config_path, dest, python)
        say(f'VERIFY OK: MCP отвечает, ZIP корректен; зарегистрировано MCP-серверов: {count}.')
        say('Это не подтверждает наличие плагина в аккаунте или статус Running в интерфейсе Claude.')
    else:
        result = uninstall(config_path, dest)
        if result is None:
            say('Запись DAG Chat MCP отсутствует — удалять нечего.')
        else:
            say('UNINSTALL OK: удалена только запись DAG Chat MCP. Резервная копия: ' + str(result))
        say('Данные DAG и ZIP плагина сохранены. Plugin Cowork удаляется отдельно через Claude > Plugins.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except InstallerError as exc:
        print('ERROR: ' + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
    except Exception as exc:
        print('UNEXPECTED ERROR: ' + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(3)
