#!/usr/bin/env python3
"""
存储层离线单元测试：不依赖真实 API / 网络，仅覆盖 JsonStore、ScopedMemoryStore
与 AIRepository 的核心读写、round-trip、heal 以及本次防御性修复（getter 返回副本）。

用法: python3 -m unittest test.test_storage -v
"""

import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pack.json_store import JsonStore
from pack.scoped_memory_store import ScopedMemoryStore, scope_filename
from core.ai_repository import AIRepository


class JsonStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, 'state.json')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_init(self):
        store = JsonStore(self.path)
        self.assertEqual(store.load(), {})

    def test_update_roundtrip(self):
        store = JsonStore(self.path)
        result = store.update(lambda p: p.setdefault('agents', {}).setdefault('k', {'n': 1}))
        self.assertEqual(store.load(), {'agents': {'k': {'n': 1}}})
        self.assertEqual(result, {'n': 1})

    def test_update_returns_mutator_result(self):
        store = JsonStore(self.path)
        out = store.update(lambda p: 42)
        self.assertEqual(out, 42)

    def test_save_persists_across_instances(self):
        store = JsonStore(self.path)
        store.save({'x': 1})
        store2 = JsonStore(self.path)
        self.assertEqual(store2.load(), {'x': 1})

    def test_heal_junk_suffix(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write('{"a": 1} trailing junk')
        store = JsonStore(self.path)
        self.assertEqual(store.load(), {'a': 1})
        # heal 后重新实例化，验证落盘内容已被修复
        store2 = JsonStore(self.path)
        self.assertEqual(store2.load(), {'a': 1})


class ScopedMemoryStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = ScopedMemoryStore(os.path.join(self.tmp, 'memories'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scope_filename_safety(self):
        self.assertEqual(scope_filename('group:123'), 'group__123.json')
        self.assertEqual(scope_filename('private:999'), 'private__999.json')
        self.assertEqual(scope_filename('weird/../key'), 'unknown__weird____key.json')

    def test_independent_files(self):
        self.store.update('group:1', lambda m: m.update({'messages': ['a']}))
        self.store.update('group:2', lambda m: m.update({'messages': ['b']}))
        self.assertEqual(self.store.load('group:1'), {'messages': ['a']})
        self.assertEqual(self.store.load('group:2'), {'messages': ['b']})

    def test_list_scopes(self):
        self.store.update('group:1', lambda m: m)
        self.store.update('group:2', lambda m: m)
        names = set(self.store.list_scopes())
        self.assertEqual(names, {'group__1.json', 'group__2.json'})


class AIRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        store = JsonStore(os.path.join(self.tmp, 'state.json'))
        self.repo = AIRepository(store)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_get_agent_returns_copy(self):
        self.repo.get_or_create_agent('group', '123')
        first = self.repo.get_agent('group', '123')
        self.assertIsNotNone(first)
        # 修改返回 dict 不应污染 store 缓存
        first['display_name'] = 'POLLUTED'
        again = self.repo.get_agent('group', '123')
        self.assertNotEqual(again.get('display_name'), 'POLLUTED')

    def test_get_scope_relation_returns_copy(self):
        self.repo.update_scope_relation('group', '123', affinity=1.0)
        first = self.repo.get_scope_relation('group', '123')
        self.assertIsNotNone(first)
        first['affinity'] = 999.0
        again = self.repo.get_scope_relation('group', '123')
        self.assertEqual(again.get('affinity'), 1.0)

    def test_setting_roundtrip(self):
        self.assertIsNone(self.repo.get_setting('foo'))
        self.repo.set_setting('foo', 'bar')
        self.assertEqual(self.repo.get_setting('foo'), 'bar')

    def test_knowledge_base_crud(self):
        entry = self.repo.add_knowledge_entry('hello world')
        self.assertIsNotNone(entry)
        self.assertEqual(self.repo.get_knowledge_base(), [entry])
        updated = self.repo.update_knowledge_entry(entry['entry_id'], 'updated')
        self.assertEqual(updated['content'], 'updated')
        self.assertTrue(self.repo.delete_knowledge_entry(entry['entry_id']))
        self.assertEqual(self.repo.get_knowledge_base(), [])

    def test_touch_user_identity_and_profile(self):
        self.repo.touch_user_identity('1001', 'Alice', 'private', '1001')
        profile = self.repo.get_user_profile('1001')
        self.assertIsNotNone(profile)
        self.assertIn('Alice', profile.get('aliases') or [])

    def test_append_message_updates_count_and_memory(self):
        agent = self.repo.get_or_create_agent('group', '7')
        self.assertEqual(agent.message_count, 0)
        self.repo.append_message('group', '7', {'user_id': '1', 'text': 'hi'}, limit=50)
        memory = self.repo.get_memory('group', '7')
        self.assertEqual(len(memory.get('messages') or []), 1)
        again = self.repo.get_or_create_agent('group', '7')
        self.assertEqual(again.message_count, 1)


if __name__ == '__main__':
    unittest.main()
