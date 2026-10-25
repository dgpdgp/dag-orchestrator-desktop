#!/usr/bin/env python3
"""Independent local MCP smoke test. Uses a temporary DAG_STATE_DIR; no project files modified."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'mcp' / 'server.py'

def check():
    with tempfile.TemporaryDirectory(prefix='dag-smoke-') as folder:
        env = dict(os.environ, DAG_STATE_DIR=folder)
        sequence = [
            {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18', 'capabilities': {}, 'clientInfo': {'name':'smoke', 'version':'1'}}},
            {'jsonrpc':'2.0','method':'notifications/initialized'},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'dag_create','arguments':{'graph_id':'smoke','title':'Smoke test','tasks':[{'id':'a','title':'First'},{'id':'b','title':'Second','depends_on':['a']}]}}},
            {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'dag_ready','arguments':{'graph_id':'smoke'}}},
        ]
        proc = subprocess.run([sys.executable, str(SERVER)], input='\n'.join(map(json.dumps, sequence))+'\n', text=True, capture_output=True, env=env, timeout=15)
        if proc.returncode:
            raise RuntimeError(proc.stderr or 'server exited with failure')
        responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        assert len(responses) == 4, responses
        assert len(responses[1]['result']['tools']) >= 10
        assert 'isError' not in responses[2]['result']
        ready = json.loads(responses[3]['result']['content'][0]['text'])['ready']
        assert [node['id'] for node in ready] == ['a'], ready
        assert (Path(folder) / 'smoke.json').exists()
        print('PASS: MCP handshake, tools/list, create, dependency gate, persisted state.')
        print('This does NOT verify Claude Desktop integration on this computer.')

if __name__ == '__main__':
    try:
        check()
    except Exception as exc:
        print('FAIL:', exc, file=sys.stderr)
        raise SystemExit(1)
