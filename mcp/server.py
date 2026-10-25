#!/usr/bin/env python3
"""DAG Orchestrator Desktop MCP server (stdio; Python 3.10+, stdlib only).

Stores plans/status, validates dependencies and serializes writes. It does NOT
spawn agents, execute commands, modify project files, or claim to run tests.
"""
from __future__ import annotations
import json
import hashlib
import os
import re
import secrets
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SERVER_VERSION = '2.3.0'
DEFAULT_PROTOCOL = '2025-06-18'
ID_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$')
MAX_TASKS = 150
MAX_RETRIES = 3
MAX_MESSAGE_BYTES = 4 * 1024 * 1024
STATE_DIR = Path(os.environ.get('DAG_STATE_DIR') or (Path.home() / '.dag-orchestrator-desktop' / 'state'))


class JsonRpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def fail(message):
    raise ValueError(message)


def text_field(value, name, limit=4000, required=False):
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        fail(f'{name}: expected string (max {limit} characters)')
    return value


def task_id(value):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        fail('ID may contain only letters, digits, underscore and hyphen (1–64 chars)')
    return value


def validate_list_strings(value, field, limit=40):
    if not isinstance(value, list) or len(value) > limit:
        fail(f'{field} must be a list of at most {limit} strings')
    result = []
    for item in value:
        result.append(text_field(item, field, 300, required=True))
    if len(set(result)) != len(result):
        fail(f'{field} contains duplicates')
    return result


# Rules are intentionally platform-independent: a graph created on Linux must
# remain safe when replayed on the default Windows installation.
WINDOWS_DEVICES = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$',
                   *(f'COM{i}' for i in range(1, 10)),
                   *(f'LPT{i}' for i in range(1, 10)),
                   *(f'{prefix}{suffix}' for prefix in ('COM', 'LPT')
                     for suffix in ('¹', '²', '³'))}


def normalize_file_ownership(paths):
    out, seen = [], set()
    for original in paths:
        p = original.replace('\\', '/')
        if p != p.strip():
            fail('owned_files has ambiguous leading/trailing whitespace')
        if not p or p.startswith('/') or ':' in p or '\x00' in p or p.startswith('//'):
            fail('owned_files must be safe, project-relative paths')
        if any(ch in p for ch in '<>"|') or any(ord(ch) < 32 for ch in p):
            fail('owned_files contains a Windows-invalid character')
        parts = p.split('/')
        if any(not part or part in ('.', '..') or part.endswith((' ', '.')) for part in parts):
            fail('ambiguous owned_files path component')
        for part in parts:
            if part.split('.')[0].upper() in WINDOWS_DEVICES:
                fail('reserved Windows device name in owned_files')
        # A wildcard here is a deliberately coarse project lock, not a filename.
        # Permit only '*' or 'folder/*'; do not accept globs inside filenames.
        if '*' in p or '?' in p:
            if p != '*' and (parts[-1] != '*' or any('*' in x or '?' in x for x in parts[:-1])):
                fail('use only * or directory/* as a coarse owned_files lock')
        folded = p.casefold()
        if folded in seen:
            fail('owned_files contains duplicate paths after Windows normalization')
        seen.add(folded)
        out.append(p)
    return out


def conflicting_paths(a, b):
    # For uncertain wildcard ownership, serialize rather than risk overwrites.
    if '*' in a or '?' in a or '*' in b or '?' in b:
        return True
    # Windows filesystems normally compare path names case-insensitively.
    a, b = a.casefold(), b.casefold()
    return a == b or a.startswith(b.rstrip('/') + '/') or b.startswith(a.rstrip('/') + '/')


def conflicts(a, b):
    if {x.casefold() for x in a['locks']} & {x.casefold() for x in b['locks']}:
        return True
    return any(conflicting_paths(x, y) for x in a['owned_files'] for y in b['owned_files'])


def validate_graph(graph_id, title, items):
    task_id(graph_id)
    text_field(title, 'title', 200, required=True)
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_TASKS:
        fail(f'tasks must be a list of 1–{MAX_TASKS} items')
    tasks = {}
    for obj in items:
        if not isinstance(obj, dict):
            fail('each task must be an object')
        t = task_id(obj.get('id'))
        if t in tasks:
            fail(f'duplicate task id: {t}')
        parents = validate_list_strings(obj.get('depends_on', []), 'depends_on')
        for p in parents:
            task_id(p)
        tasks[t] = {
            'id': t,
            'title': text_field(obj.get('title'), f'{t}.title', 200, True),
            'depends_on': parents,
            'instructions': text_field(obj.get('instructions', ''), f'{t}.instructions', 6000),
            'acceptance': validate_list_strings(obj.get('acceptance', []), 'acceptance'),
            'owned_files': normalize_file_ownership(validate_list_strings(obj.get('owned_files', []), 'owned_files')),
            'locks': validate_list_strings(obj.get('locks', []), 'locks'),
            'max_retries': obj.get('max_retries', 1),
            'status': 'pending', 'attempts': 0, 'worker': None, 'token': None,
            'lease_expires_at': 0, 'started_at': None, 'completed_at': None,
            'output_summary': None, 'artifacts': [], 'last_error': None,
            'checks_reported_passed': False, 'completion_receipt': None
        }
        if type(tasks[t]['max_retries']) is not int or not 0 <= tasks[t]['max_retries'] <= MAX_RETRIES:
            fail(f'{t}.max_retries must be integer 0–{MAX_RETRIES}')
    for t, node in tasks.items():
        for p in node['depends_on']:
            if p not in tasks:
                fail(f'{t}: missing parent {p}')
            if p == t:
                fail(f'{t}: self-dependency')
    # Reserve a bounded graph size to prevent recursive DFS depth issues.
    visiting, done = set(), set()
    def dfs(k):
        if k in visiting:
            fail('cycle detected: graph is not a DAG')
        if k in done:
            return
        visiting.add(k)
        for p in tasks[k]['depends_on']:
            dfs(p)
        visiting.remove(k)
        done.add(k)
    for t in tasks:
        dfs(t)
    return {'schema_version': 1, 'graph_id': graph_id, 'title': title,
            'created_at': now(), 'updated_at': now(), 'revision': 0,
            'paused': False, 'tasks': tasks, 'events': []}


def state_path(graph_id):
    return STATE_DIR / (task_id(graph_id) + '.json')


@contextmanager
def lock_graph(graph_id):
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    lockfile = STATE_DIR / (task_id(graph_id) + '.lock')
    f = open(lockfile, 'a+b')
    try:
        # Lock a stable byte, never replace the lock file.
        f.seek(0, os.SEEK_END)
        if f.tell() == 0:
            f.write(b'0')
            f.flush()
        deadline = time.monotonic() + 10
        while True:
            try:
                f.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    fail('DAG state busy: retry after a moment')
                time.sleep(.06)
        yield
    finally:
        try:
            f.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()


def load(graph_id):
    p = state_path(graph_id)
    if not p.exists():
        fail(f'Unknown graph: {graph_id}')
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def save(state):
    state['updated_at'] = now()
    state['revision'] += 1
    p = state_path(state['graph_id'])
    raw = json.dumps(state, ensure_ascii=False, indent=2)
    # Retain one last-known-good revision for explicit manual recovery.
    # NEVER automatically accept a backup in place of a corrupted current state:
    # that could silently discard an acknowledged completion.
    if p.exists():
        backup_raw = p.read_bytes()
        backup_tmp = None
        try:
            bfd, backup_tmp = tempfile.mkstemp(prefix='.backup-', suffix='.tmp', dir=str(STATE_DIR))
            with os.fdopen(bfd, 'wb') as bf:
                bf.write(backup_raw)
                bf.flush()
                os.fsync(bf.fileno())
            os.replace(backup_tmp, p.with_suffix('.json.bak'))
        finally:
            if backup_tmp and os.path.exists(backup_tmp):
                os.unlink(backup_tmp)
    fd, tmp = tempfile.mkstemp(prefix='.dag-', suffix='.tmp', dir=str(STATE_DIR))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def record(state, event, t=None, **extra):
    state['events'].append({'at': now(), 'event': event, 'task': t, **extra})
    state['events'] = state['events'][-200:]


def compact_task(t):
    return {k: v for k, v in t.items()
            if k not in ('token', 'lease_expires_at', 'completion_receipt')}


def public_task(t):
    # Status may be inspected by any agent that can invoke the tool. Parent
    # outputs must only flow through dag_claim.dependency_outputs.
    fields = ('id', 'title', 'depends_on', 'status', 'attempts', 'started_at',
              'completed_at', 'checks_reported_passed')
    return {k: t[k] for k in fields}


def completed_digest(token):
    # Claim tokens have ~192 bits of entropy and are not guessable from a hash.
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def ready_tasks(state):
    if state['paused']:
        return []
    tasks = state['tasks']
    running = [t for t in tasks.values() if t['status'] == 'in_progress']
    return [t for t in tasks.values() if t['status'] == 'pending'
            and all(tasks[p]['status'] == 'completed' for p in t['depends_on'])
            and not any(conflicts(t, r) for r in running)]


def parallel_batch(state):
    """One deterministic, pairwise nonconflicting subset of presently ready tasks."""
    selected = []
    for task in ready_tasks(state):
        if not any(conflicts(task, other) for other in selected):
            selected.append(task)
    return selected


def dispatch(name, args):
    if not isinstance(args, dict):
        fail('arguments must be an object')
    if name == 'dag_create':
        state = validate_graph(args.get('graph_id'), args.get('title'), args.get('tasks'))
        with lock_graph(state['graph_id']):
            if state_path(state['graph_id']).exists():
                fail('graph already exists; use dag_status to resume; never overwrite a plan')
            record(state, 'created')
            save(state)
        return {'graph_id': state['graph_id'], 'tasks': len(state['tasks']), 'revision': state['revision']}
    graph_id = task_id(args.get('graph_id'))
    with lock_graph(graph_id):
        state = load(graph_id)
        tasks = state['tasks']
        if name == 'dag_status':
            summary = {s: sum(t['status'] == s for t in tasks.values()) for s in ('pending', 'in_progress', 'completed', 'failed')}
            blocked = {t['id']: [p for p in t['depends_on'] if tasks[p]['status'] != 'completed']
                       for t in tasks.values() if t['status'] == 'pending'
                       and any(tasks[p]['status'] != 'completed' for p in t['depends_on'])}
            return {'graph_id': graph_id, 'title': state['title'], 'paused': state['paused'],
                    'revision': state['revision'], 'counts': summary, 'blocked_by': blocked,
                    'ready': [t['id'] for t in ready_tasks(state)],
                    'parallel_batch': [t['id'] for t in parallel_batch(state)],
                    'tasks': [public_task(t) for t in tasks.values()],
                    'events': [{k: event.get(k) for k in ('at','event','task')}
                               for event in state['events'][-20:]]}
        if name == 'dag_ready':
            return {'graph_id': graph_id, 'paused': state['paused'],
                    'ready': [compact_task(t) for t in ready_tasks(state)]}
        if name == 'dag_parallel_batch':
            selected = parallel_batch(state)
            return {'graph_id': graph_id, 'paused': state['paused'],
                    'batch': [compact_task(t) for t in selected],
                    'note': 'Batch is a snapshot. Atomically claim each task before execution; claims may change readiness.'}
        if name == 'dag_pause':
            paused = args.get('paused')
            if type(paused) is not bool:
                fail('paused must be boolean')
            state['paused'] = paused
            record(state, 'paused' if paused else 'resumed')
            save(state)
            return {'paused': paused}
        if name == 'dag_recover':
            recovered = []
            for t in tasks.values():
                if t['status'] == 'in_progress' and t['lease_expires_at'] <= time.time():
                    t['status'] = 'pending' if t['attempts'] <= t['max_retries'] else 'failed'
                    t['last_error'] = 'Previous claim lease expired; verify work before retrying'
                    t['token'] = None
                    t['worker'] = None
                    t['lease_expires_at'] = 0
                    recovered.append(t['id'])
                    record(state, 'expired', t['id'])
            if recovered:
                save(state)
            return {'recovered': recovered, 'warning': 'Review partial artifacts before retrying; this does not undo file changes'}
        t_id = task_id(args.get('task_id'))
        if t_id not in tasks:
            fail('task does not exist')
        t = tasks[t_id]
        if name == 'dag_claim':
            if state['paused']:
                fail('DAG is paused')
            if t not in ready_tasks(state):
                fail('not ready: parents incomplete, owned files locked, or already claimed')
            worker = text_field(args.get('worker'), 'worker', 120, True)
            lease = args.get('lease_seconds', 3600)
            if type(lease) is not int or not 60 <= lease <= 43200:
                fail('lease_seconds must be 60–43200')
            token = secrets.token_urlsafe(24)
            t.update(status='in_progress', worker=worker, token=token,
                     lease_expires_at=time.time() + lease, started_at=now(),
                     attempts=t['attempts'] + 1, last_error=None)
            record(state, 'claimed', t_id, worker=worker, attempt=t['attempts'])
            save(state)
            return {'task': compact_task(t), 'claim_token': token, 'lease_seconds': lease,
                    'dependency_outputs': {p: {'summary': tasks[p]['output_summary'], 'artifacts': tasks[p]['artifacts']}
                                           for p in t['depends_on']}}
        if name in ('dag_complete', 'dag_fail', 'dag_heartbeat'):
            token = args.get('claim_token')
            # If a completion response was lost, the exact same token and
            # report may be replayed without reopening or duplicating work.
            if name == 'dag_complete' and t['status'] == 'completed' and isinstance(token, str):
                if (t.get('completion_receipt') == completed_digest(token)
                        and args.get('checks_passed') is True
                        and args.get('output_summary') == t['output_summary']
                        and args.get('artifacts', []) == t['artifacts']):
                    return {'task_id': t_id, 'status': 'completed', 'replayed': True,
                            'note': 'Identical completion already recorded; no state change'}
                fail('completion already recorded; replay must match original token and result')
            if t['status'] != 'in_progress' or not isinstance(token, str) or not secrets.compare_digest(token, t['token'] or ''):
                fail('task is not claimed by this token')
            if t['lease_expires_at'] <= time.time():
                fail('claim lease expired; call dag_recover and verify partial work')
            if name == 'dag_heartbeat':
                lease = args.get('lease_seconds', 3600)
                if type(lease) is not int or not 60 <= lease <= 43200:
                    fail('lease_seconds must be 60–43200')
                t['lease_expires_at'] = time.time() + lease
                record(state, 'heartbeat', t_id)
                save(state)
                return {'task_id': t_id, 'lease_seconds': lease}
            if name == 'dag_complete':
                if args.get('checks_passed') is not True:
                    fail('checks_passed=true is required; do not claim completion without verification')
                summary = text_field(args.get('output_summary'), 'output_summary', 4000, True)
                artifacts = validate_list_strings(args.get('artifacts', []), 'artifacts')
                t.update(status='completed', output_summary=summary, artifacts=artifacts,
                         checks_reported_passed=True, completion_receipt=completed_digest(token),
                         token=None, worker=None,
                         lease_expires_at=0, completed_at=now())
                record(state, 'completed', t_id)
                save(state)
                return {'task_id': t_id, 'status': 'completed', 'note': 'Checks are agent-reported; server did not run them'}
            error = text_field(args.get('error'), 'error', 2000, True)
            t.update(last_error=error, status='pending' if t['attempts'] <= t['max_retries'] else 'failed',
                     token=None, worker=None, lease_expires_at=0)
            record(state, 'failed_attempt', t_id, attempt=t['attempts'], next_status=t['status'])
            save(state)
            return {'task_id': t_id, 'status': t['status'], 'attempts': t['attempts'], 'max_retries': t['max_retries']}
        if name == 'dag_retry_failed':
            if t['status'] != 'failed':
                fail('only failed tasks can be retried')
            note = text_field(args.get('reason'), 'reason', 500, True)
            t.update(status='pending', attempts=0, last_error='Manually reset: ' + note)
            record(state, 'manual_retry', t_id, reason=note)
            save(state)
            return {'task_id': t_id, 'status': 'pending', 'warning': 'Review existing artifacts before re-running'}
        fail('Unknown tool: ' + name)


SCHEMAS = {
    'dag_create': {'graph_id': 'string', 'title': 'string', 'tasks': 'array'},
    'dag_status': {'graph_id': 'string'},
    'dag_ready': {'graph_id': 'string'},
    'dag_parallel_batch': {'graph_id': 'string'},
    'dag_claim': {'graph_id': 'string', 'task_id': 'string', 'worker': 'string'},
    'dag_complete': {'graph_id': 'string', 'task_id': 'string', 'claim_token': 'string', 'output_summary': 'string', 'checks_passed': 'boolean'},
    'dag_fail': {'graph_id': 'string', 'task_id': 'string', 'claim_token': 'string', 'error': 'string'},
    'dag_heartbeat': {'graph_id': 'string', 'task_id': 'string', 'claim_token': 'string'},
    'dag_recover': {'graph_id': 'string'},
    'dag_pause': {'graph_id': 'string', 'paused': 'boolean'},
    'dag_retry_failed': {'graph_id': 'string', 'task_id': 'string', 'reason': 'string'},
}

TOOL_DESCRIPTIONS = {
    'dag_create': 'Validate and persist new DAG. tasks: id, title, depends_on[], instructions, acceptance[], owned_files[], locks[], max_retries (0..3). Refuses cycles and overwrite.',
    'dag_status': 'Get public DAG progress without claim tokens, output summaries, worker IDs or error details.',
    'dag_ready': 'List individually claimable tasks. This list may contain mutually conflicting tasks; use dag_parallel_batch for a parallel wave.',
    'dag_parallel_batch': 'Return one pairwise nonconflicting batch from ready tasks, suitable for claim attempts before parallel dispatch.',
    'dag_claim': 'Atomically claim a ready task and receive its token and only direct-parent outputs.',
    'dag_complete': 'Report a verified completion. Requires token and checks_passed=true, with output_summary and artifacts[]. Tests are not run by this server.',
    'dag_fail': 'Report failure using claim token; may auto-requeue according to retry limit.',
    'dag_heartbeat': 'Refresh a valid lease for a running task.',
    'dag_recover': 'Explicitly expire stale claims. Does not undo file edits; verify before repeating.',
    'dag_pause': 'Pause or resume new claims without killing running tasks.',
    'dag_retry_failed': 'Manually return permanently failed task to pending after fixing root cause.',
}


def tool_def(name):
    properties = {}
    for k, typ in SCHEMAS[name].items():
        properties[k] = {'type': typ}
    optional = {
        'dag_create': {'tasks': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}}},
        'dag_claim': {'lease_seconds': {'type': 'integer', 'minimum': 60, 'maximum': 43200}},
        'dag_heartbeat': {'lease_seconds': {'type': 'integer', 'minimum': 60, 'maximum': 43200}},
        'dag_complete': {'artifacts': {'type': 'array', 'items': {'type': 'string'}}}
    }
    properties.update(optional.get(name, {}))
    return {'name': name, 'description': TOOL_DESCRIPTIONS[name],
            'inputSchema': {'type': 'object', 'properties': properties,
                            'required': list(SCHEMAS[name]), 'additionalProperties': False}}


def respond(req):
    if req.get('jsonrpc') != '2.0' or not isinstance(req.get('method'), str):
        raise JsonRpcError(-32600, 'Invalid JSON-RPC 2.0 request')
    method = req['method']
    params = req.get('params', {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise JsonRpcError(-32602, 'params must be an object')
    if method == 'initialize':
        requested = params.get('protocolVersion', DEFAULT_PROTOCOL)
        proto = requested if requested in ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25') else DEFAULT_PROTOCOL
        return {'protocolVersion': proto, 'capabilities': {'tools': {'listChanged': False}},
                'serverInfo': {'name': 'dag-orchestrator-desktop', 'version': SERVER_VERSION}}
    if method == 'ping':
        return {}
    if method == 'tools/list':
        return {'tools': [tool_def(n) for n in SCHEMAS]}
    if method == 'tools/call':
        try:
            result = dispatch(params.get('name'), params.get('arguments', {}))
            return {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}]}
        except (ValueError, TypeError, OSError) as e:
            return {'content': [{'type': 'text', 'text': str(e)}], 'isError': True}
    raise JsonRpcError(-32601, 'Method not found')


def main():
    # stdout is reserved exclusively for MCP messages. Diagnostics -> stderr.
    while True:
        # Bounded input prevents unbounded memory consumption from malicious clients.
        line = sys.stdin.buffer.readline(MAX_MESSAGE_BYTES + 1)
        if not line:
            break
        if not line.strip():
            continue
        if len(line) > MAX_MESSAGE_BYTES:
            # Consume rest of an oversized request until newline, restoring framing.
            while line and not line.endswith(b'\n'):
                line = sys.stdin.buffer.readline(MAX_MESSAGE_BYTES + 1)
            response = {'jsonrpc': '2.0', 'id': None,
                        'error': {'code': -32700, 'message': 'Request exceeds input limit'}}
        else:
            try:
                req = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                response = {'jsonrpc': '2.0', 'id': None,
                            'error': {'code': -32700, 'message': 'Parse error'}}
            else:
                if not isinstance(req, dict):
                    response = {'jsonrpc': '2.0', 'id': None,
                                'error': {'code': -32600, 'message': 'Invalid Request'}}
                elif 'id' not in req:
                    continue  # Notifications do not generate responses.
                else:
                    try:
                        result = respond(req)
                        response = {'jsonrpc': '2.0', 'id': req['id'], 'result': result}
                    except JsonRpcError as e:
                        response = {'jsonrpc': '2.0', 'id': req['id'],
                                    'error': {'code': e.code, 'message': str(e)}}
                    except Exception as e:
                        print(f'MCP internal error: {type(e).__name__}', file=sys.stderr)
                        response = {'jsonrpc': '2.0', 'id': req['id'],
                                    'error': {'code': -32603, 'message': 'Internal error'}}
        sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(',', ':')) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
