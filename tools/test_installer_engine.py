"""Platform-independent unit/integration tests; actual Windows runs are still required."""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer_engine', ROOT / 'installer_engine.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.ctx = tempfile.TemporaryDirectory(prefix='dag-installer-t-')
        self.addCleanup(self.ctx.cleanup)
        self.root = Path(self.ctx.name)
        self.config = self.root / 'Claude' / 'claude_desktop_config.json'
        self.config.parent.mkdir()
        self.dest = self.root / 'Local' / 'DAGOrchestratorDesktop'
        self.original = {'preferences':{'sidebarMode':'chat','test':True},
                         'mcpServers':{'memory':{'command':'node','args':['some-script.js']},
                                       'filesystem':{'command':'node','args':['fs.js']}},
                         'other':{'nested':{'very':{'deep':[1,2,3]}}}}
        self.config.write_text(json.dumps(self.original), encoding='utf-8')
        self.python = e.checked_python()

    def test_01_smoke_real_server(self):
        self.assertTrue(e.run_smoke(e.SERVER,self.python))

    def test_02_install_preserves_other_servers(self):
        answer = e.install(self.config,self.dest,self.python,publish_local_copy=False)
        self.assertTrue(Path(answer['backup']).exists())
        self.assertEqual(json.loads(Path(answer['backup']).read_text()), self.original)
        obj = e.load_json(self.config)
        self.assertEqual(obj['mcpServers']['memory'],self.original['mcpServers']['memory'])
        self.assertEqual(obj['mcpServers']['filesystem'],self.original['mcpServers']['filesystem'])
        self.assertEqual(obj['preferences'],self.original['preferences'])
        self.assertEqual(obj['other'],self.original['other'])
        self.assertEqual(obj['mcpServers'][e.NAME]['command'],str(self.python))
        self.assertEqual(e.verify(self.config,self.dest,self.python),3)

    def test_03_update_is_idempotent(self):
        e.install(self.config,self.dest,self.python,publish_local_copy=False)
        e.install(self.config,self.dest,self.python,publish_local_copy=False)
        self.assertEqual(len(e.load_json(self.config)['mcpServers']),3)
        self.assertGreaterEqual(len(list(self.config.parent.glob('*.backup-DAG-*'))),2)

    def test_04_uninstall_is_targeted(self):
        e.install(self.config,self.dest,self.python,publish_local_copy=False)
        backup = e.uninstall(self.config,self.dest)
        self.assertTrue(backup.is_file())
        self.assertEqual(e.load_json(self.config),self.original)
        self.assertTrue((self.dest / 'server.py').exists())
        self.assertIsNone(e.uninstall(self.config,self.dest))

    def test_05_collision_does_not_override(self):
        collision = copy.deepcopy(self.original)
        collision['mcpServers'][e.NAME]={'command':'other.exe','args':['private-server.py']}
        self.config.write_text(json.dumps(collision), encoding='utf-8')
        with self.assertRaises(e.InstallerError):
            e.install(self.config,self.dest,self.python,publish_local_copy=False)
        self.assertEqual(e.load_json(self.config),collision)

    def test_06_invalid_json_fails_closed(self):
        self.config.write_text('{"broken":', encoding='utf-8')
        with self.assertRaises(e.InstallerError):
            e.install(self.config,self.dest,self.python,publish_local_copy=False)
        self.assertEqual(self.config.read_text(),'{"broken":')

    def test_07_non_object_json_fails_closed(self):
        self.config.write_text('[]',encoding='utf-8')
        with self.assertRaises(e.InstallerError):e.load_json(self.config)

    def test_08_duplicate_keys_fails_closed(self):
        self.config.write_text('{"mcpServers":{},"mcpServers":{}}',encoding='utf-8')
        with self.assertRaises(e.InstallerError):e.load_json(self.config)

    def test_09_valid_plugin_zip_and_paths(self):
        zpath = self.root / 'plugin.zip'
        e.make_plugin_zip(zpath,self.python)
        with zipfile.ZipFile(zpath) as z:
            names=z.namelist()
            self.assertTrue(all('\\' not in x for x in names))
            self.assertIn('.claude-plugin/plugin.json',names)
            plugin=json.loads(z.read('.mcp.json'))
            self.assertEqual(plugin['mcpServers'][e.NAME]['command'],str(self.python))
            self.assertIn('${CLAUDE_PLUGIN_ROOT}/mcp/server.py',plugin['mcpServers'][e.NAME]['args'])

    def test_10_store_config_from_active_family(self):
        appdata=self.root/'Roaming'
        local=self.root/'Local'
        active=local/'Packages'/'Claude_ACTIVE'/'LocalCache'/'Roaming'/'Claude'/'claude_desktop_config.json'
        stale=local/'Packages'/'Claude_STALE'/'LocalCache'/'Roaming'/'Claude'/'claude_desktop_config.json'
        for path in (active,stale):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('{}')
        selected,kind=e.discover_config(appdata,local,['Claude_ACTIVE'])
        self.assertEqual(selected,active)
        self.assertIn('MSIX',kind)

    def test_11_ambiguous_msix_fails_closed(self):
        local=self.root/'Local'; appdata=self.root/'Roaming'
        for name in ('Claude_A','Claude_B'):
            path=local/'Packages'/name/'LocalCache'/'Roaming'/'Claude'/'claude_desktop_config.json'
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('{}')
        with self.assertRaises(e.InstallerError):
            e.discover_config(appdata,local,[])

    def test_12_classic_fallback(self):
        appdata=self.root/'Roaming'; local=self.root/'Local'
        target=appdata/'Claude'/'claude_desktop_config.json'
        target.parent.mkdir(parents=True,exist_ok=True); target.write_text('{}')
        selected,kind=e.discover_config(appdata,local,[])
        self.assertEqual(selected,target)
        self.assertEqual(kind,'Classic')

    def test_13_read_bom(self):
        self.config.write_bytes(b'\xef\xbb\xbf'+json.dumps(self.original).encode())
        self.assertIn('mcpServers',e.load_json(self.config))

    def test_14_missing_installed_file_verify_fails(self):
        e.install(self.config,self.dest,self.python,publish_local_copy=False)
        (self.dest/'server.py').unlink()
        with self.assertRaises(e.InstallerError):e.verify(self.config,self.dest,self.python)

    def test_15_no_mutation_outside_target(self):
        data=self.root/'unrelated'/'important.txt'
        data.parent.mkdir(); data.write_text('keep unchanged')
        e.install(self.config,self.dest,self.python,publish_local_copy=False)
        self.assertEqual(data.read_text(),'keep unchanged')

    def test_17_rollback_if_config_update_fails(self):
        from unittest import mock
        self.dest.mkdir(parents=True, exist_ok=True)
        (self.dest/'server.py').write_bytes(b'old valid server placeholder')
        (self.dest/e.PLUGIN_FILE).write_bytes(b'old plugin placeholder')
        original=self.config.read_bytes()
        with mock.patch.object(e, 'write_config', side_effect=OSError('simulated disk failure')):
            with self.assertRaises(OSError):
                e.install(self.config,self.dest,self.python,publish_local_copy=False)
        self.assertEqual(self.config.read_bytes(),original)
        self.assertEqual((self.dest/'server.py').read_bytes(),b'old valid server placeholder')
        self.assertEqual((self.dest/e.PLUGIN_FILE).read_bytes(),b'old plugin placeholder')

    def test_18_uninstall_refuses_to_touch_other_server(self):
        content=copy.deepcopy(self.original)
        content['mcpServers'][e.NAME]={'command':'cmd','args':['external.py']}
        self.config.write_text(json.dumps(content),encoding='utf-8')
        with self.assertRaises(e.InstallerError):e.uninstall(self.config,self.dest)
        self.assertEqual(e.load_json(self.config),content)

    def test_19_manifest_integrity_before_install(self):
        self.assertGreaterEqual(e.verify_manifest(),10)

    def test_16_verify_config_detects_changed_command(self):
        e.install(self.config,self.dest,self.python,publish_local_copy=False)
        doc=e.load_json(self.config)
        doc['mcpServers'][e.NAME]['args']=['wrong.py']
        self.config.write_text(json.dumps(doc),encoding='utf-8')
        with self.assertRaises(e.InstallerError):e.verify(self.config,self.dest,self.python)


if __name__ == '__main__':
    unittest.main(verbosity=2)
