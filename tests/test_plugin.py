from unittest.mock import Mock

import pytest

from doit.plugin import PluginEntry, PluginDict


class TestPluginEntry(object):
    def test_repr(self):
        plugin = PluginEntry('category1', 'name1', 'mock:Mock')
        assert "PluginEntry('category1', 'name1', 'mock:Mock')" == repr(plugin)

    def test_get(self):
        plugin = PluginEntry('category1', 'name1', 'unittest.mock:Mock')
        got = plugin.get()
        assert got is Mock

    def test_load_error_module_not_found(self):
        plugin = PluginEntry('category1', 'name1', 'i_dont:exist')
        with pytest.raises(Exception) as exc_info:
            plugin.load()
        assert 'Plugin category1 module `i_dont`' in str(exc_info.value)

    def test_load_error_obj_not_found(self):
        plugin = PluginEntry('category1', 'name1',
                             'unittest.mock:i_dont_exist')
        with pytest.raises(Exception) as exc_info:
            plugin.load()
        assert ('Plugin category1:name1 module `unittest.mock`' in
                str(exc_info.value))
        assert 'i_dont_exist' in str(exc_info.value)


class TestPluginDict(object):

    @pytest.fixture
    def plugins(self):
        plugins = PluginDict()
        config_dict = {'name1': 'pytest:raises',
                       'name2': 'unittest.mock:Mock'}
        plugins.add_plugins({'category1': config_dict}, 'category1')
        return plugins

    def test_add_plugins_from_dict(self, plugins):
        assert len(plugins) == 2
        name1 = plugins['name1']
        assert isinstance(name1, PluginEntry)
        assert name1.category == 'category1'
        assert name1.name == 'name1'
        assert name1.location == 'pytest:raises'

    def test_add_plugins_from_pkg_resources(self, monkeypatch):
        # mock entry points
        import pkg_resources
        def fake_entries(group):
            yield pkg_resources.EntryPoint('name1', 'pytest', ('raises',))
        monkeypatch.setattr(pkg_resources, 'iter_entry_points', fake_entries)

        plugins = PluginDict()
        plugins.add_plugins({}, 'category2')
        name1 = plugins['name1']
        assert isinstance(name1, PluginEntry)
        assert name1.category == 'category2'
        assert name1.name == 'name1'
        assert name1.location == 'pytest:raises'

    def test_get_plugin_actual_plugin(self, plugins):
        assert plugins.get_plugin('name2') is Mock

    def test_get_plugin_not_a_plugin(self, plugins):
        my_val = 4
        plugins['builtin-item'] = my_val
        assert plugins.get_plugin('builtin-item') is my_val

    def test_to_dict(self, plugins):
        expected = {'name1': pytest.raises,
                    'name2': Mock}
        assert plugins.to_dict() == expected
