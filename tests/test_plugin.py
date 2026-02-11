import unittest
from importlib.metadata import EntryPoint
from unittest.mock import Mock, patch

from doit.plugin import PluginEntry, PluginDict
from doit import plugin


class TestPluginEntry(unittest.TestCase):
    def test_repr(self):
        pe = PluginEntry('category1', 'name1', 'mock:Mock')
        self.assertEqual("PluginEntry('category1', 'name1', 'mock:Mock')", repr(pe))

    def test_get(self):
        pe = PluginEntry('category1', 'name1', 'unittest.mock:Mock')
        got = pe.get()
        self.assertIs(got, Mock)

    def test_load_error_module_not_found(self):
        pe = PluginEntry('category1', 'name1', 'i_dont:exist')
        with self.assertRaises(Exception) as cm:
            pe.load()
        self.assertIn('Plugin category1 module `i_dont`', str(cm.exception))

    def test_load_error_obj_not_found(self):
        pe = PluginEntry('category1', 'name1',
                         'unittest.mock:i_dont_exist')
        with self.assertRaises(Exception) as cm:
            pe.load()
        self.assertIn('Plugin category1:name1 module `unittest.mock`',
                      str(cm.exception))
        self.assertIn('i_dont_exist', str(cm.exception))


class TestPluginDict(unittest.TestCase):

    def _make_plugins(self):
        plugins = PluginDict()
        config_dict = {'name1': 'json:loads',
                       'name2': 'unittest.mock:Mock'}
        plugins.add_plugins({'category1': config_dict}, 'category1')
        return plugins

    def test_add_plugins_from_dict(self):
        plugins = self._make_plugins()
        self.assertEqual(2, len(plugins))
        name1 = plugins['name1']
        self.assertIsInstance(name1, PluginEntry)
        self.assertEqual('category1', name1.category)
        self.assertEqual('name1', name1.name)
        self.assertEqual('json:loads', name1.location)

    def test_add_plugins_from_pkg_resources(self):
        # mock entry points
        def fake_entries(group):
            yield EntryPoint(name='name1', value='json:loads', group=group)

        with patch.object(plugin, 'entry_points_impl', lambda: fake_entries):
            plugins = PluginDict()
            plugins.add_plugins({}, 'category2')
        name1 = plugins['name1']
        self.assertIsInstance(name1, PluginEntry)
        self.assertEqual('category2', name1.category)
        self.assertEqual('name1', name1.name)
        self.assertEqual('json:loads', name1.location)

    def test_get_plugin_actual_plugin(self):
        plugins = self._make_plugins()
        self.assertIs(Mock, plugins.get_plugin('name2'))

    def test_get_plugin_not_a_plugin(self):
        plugins = self._make_plugins()
        my_val = 4
        plugins['builtin-item'] = my_val
        self.assertIs(my_val, plugins.get_plugin('builtin-item'))

    def test_to_dict(self):
        import json as json_mod
        plugins = self._make_plugins()
        expected = {'name1': json_mod.loads,
                    'name2': Mock}
        self.assertEqual(expected, plugins.to_dict())
