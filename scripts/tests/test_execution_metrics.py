import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from execution_metrics import TraceCollection, TraceReader, execution_report
from test_dashboard import fixture_run, write
import dashboard


class ExecutionMetricsTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[2] / '.test-tmp'
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='metrics-', dir=base)
        assert Path(self.temp.name).resolve().is_relative_to(base.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def trace(self, name, source='vscode'):
        path = self.root / f'{name}.jsonl'
        self.append(path, 'session_meta', {'id': name, 'timestamp': '2026-09-20T00:00:00Z', 'source': source})
        return path

    def append(self, path, kind, data):
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': kind, 'payload': data, 'timestamp': '2026-09-20T01:00:00Z'})+'\n')

    def test_incremental_dedup_and_own_usage_only(self):
        path = self.trace('worker')
        self.append(path, 'response_item', {'type': 'function_call', 'name': 'exec', 'call_id': 'inherited-before-context'})
        self.append(path, 'turn_context', {'turn_id': 'turn1', 'model': 'model-a', 'effort': 'medium'})
        call = {'type': 'function_call', 'name': 'exec', 'call_id': 'own-call'}
        self.append(path, 'response_item', call)
        self.append(path, 'response_item', call)
        usage = {'thread_id': 'worker', 'response_id': 'response1', 'usage': {'input_tokens': 100, 'cached_input_tokens': 80, 'output_tokens': 12, 'reasoning_output_tokens': 4}}
        for _ in range(2): self.append(path, 'token_usage_record', usage)
        self.append(path, 'token_usage_record', {**usage, 'thread_id': 'parent', 'response_id': 'other'})
        self.append(path, 'event_msg', {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': 9999}}})
        reader = TraceReader(path)
        report = reader.read()
        self.assertEqual(report['host_tool_requests'], 1)
        self.assertEqual(report['tokens'], usage['usage'])
        self.assertEqual(reader.read(), report)
        self.append(path, 'response_item', {**call, 'call_id': 'second'})
        self.assertEqual(reader.read()['host_tool_requests'], 2)

    def test_partial_write_is_retried(self):
        path = self.trace('main')
        self.append(path, 'turn_context', {'turn_id': 'turn1'})
        item = json.dumps({'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec', 'call_id': 'call'}})
        with path.open('a') as stream: stream.write(item[:30])
        reader = TraceReader(path)
        self.assertEqual(reader.read()['host_tool_requests'], 0)
        with path.open('a') as stream: stream.write(item[30:]+'\n')
        self.assertEqual(reader.read()['host_tool_requests'], 1)

    def test_descendants_discovered_guardians_excluded(self):
        main = self.trace('main')
        self.trace('child', {'subagent': {'thread_spawn': {'parent_thread_id': 'main'}}})
        self.trace('grandchild', {'subagent': {'thread_spawn': {'parent_thread_id': 'child'}}})
        self.trace('guardian', {'subagent': {'other': 'guardian'}})
        self.trace('unrelated')
        report = TraceCollection([main]).read()
        self.assertEqual({s['id'] for s in report['sessions']}, {'main','child','grandchild'})

    def valid_metrics(self):
        return {'schema_version':1, 'coverage':'partial', 'call_unit':'underlying_tools', 'executors':[
            {'kind':'orchestrator','id':'director','measurement':'estimated','tool_calls':5,
             'implementation_calls':None,'input_tokens':None}], 'limitations':['Estimate, not a trace count']}

    def test_unknowns_stay_unknown_and_double_counting_rejected(self):
        self.assertEqual(execution_report(None)['coverage'], 'unknown')
        value = self.valid_metrics()
        self.assertIsNone(execution_report(value)['executors'][0]['input_tokens'])
        for bad in (-1, float('nan'), True):
            value['executors'][0]['tool_calls'] = bad
            with self.assertRaises(ValueError): execution_report(value)
        value = self.valid_metrics()
        value['executors'][0].update(implementation_calls=4, verification_calls=4, coordination_calls=1)
        with self.assertRaises(ValueError): execution_report(value)
        value = self.valid_metrics()
        value['executors'][0].update(input_tokens=10,cached_input_tokens=11)
        with self.assertRaises(ValueError): execution_report(value)

    def test_sidecar_and_result_execution_without_changing_run(self):
        run = fixture_run(self.root)
        original = (run/'run.json').read_bytes()
        self.assertEqual(dashboard.snapshot(run)['packets'][0]['execution']['coverage'], 'unknown')
        write(run,'metrics/shared-system.json', self.valid_metrics())
        packet = dashboard.snapshot(run)['packets'][0]
        self.assertEqual(packet['execution']['executors'][0]['kind'], 'orchestrator')
        self.assertEqual(packet['execution']['coverage'], 'partial')
        self.assertEqual((run/'run.json').read_bytes(), original)
        write(run,'metrics/shared-system.json', {'schema_version':99})
        report = dashboard.snapshot(run)
        self.assertTrue(any('Invalid executor metrics' in w for w in report['warnings']))
        self.assertEqual(report['packets'][0]['execution']['coverage'], 'unknown')

    def test_reuse_decision_and_incomplete_token_measurement(self):
        value = self.valid_metrics()
        value['reuse_decision'] = {'decision':'adapt', 'candidates':['template feature'], 'reason':'Preserve shared input contract'}
        self.assertEqual(execution_report(value)['reuse_decision']['decision'], 'adapt')
        value['reuse_decision']['candidates'] = 'not a list'
        with self.assertRaises(ValueError): execution_report(value)
        path = self.trace('main')
        self.append(path, 'token_usage_record', {'thread_id':'main','response_id':'one','usage':{'input_tokens':100}})
        self.append(path, 'token_usage_record', {'thread_id':'main','response_id':'two','usage':{'input_tokens':50,'cached_input_tokens':10}})
        tokens = TraceReader(path).read()['tokens']
        self.assertEqual(tokens['input_tokens'], 150)
        self.assertIsNone(tokens['cached_input_tokens'])
        self.assertIsNone(tokens['output_tokens'])


if __name__ == '__main__':
    unittest.main()
