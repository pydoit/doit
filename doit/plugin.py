import importlib

class PluginEntry(object):
    class Sentinel(object):
        pass
    NOT_LOADED = Sentinel()
    def __init__(self, category, name, location):
        self.obj = self.NOT_LOADED
        self.category = category
        self.name = name
        self.location = location

    def get(self):
        """return obj, get from cache or load"""
        if self.obj is self.NOT_LOADED:
            self.obj = self.load()
        return self.obj

    def load(self):
        """load/import reference to obj from named module/obj"""
        module_name, obj_name = self.location.split(':')
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            raise Exception('Plugin {} module `{}` not found.'.format(
                self.category, module_name))
        try:
            obj = getattr(module, obj_name)
        except AttributeError:
            raise Exception('Plugin {}:{} module `{}` has no {}.'.format(
                self.category, self.name, module_name, obj_name))
        return obj


class PluginDict(dict):
    """A dict where item values *might* be a PluginEntry"""

    def add_plugins(self, section, cfg_dict):
        for name, location in cfg_dict.items():
            self[name] = PluginEntry(section, name, location)

    def get_plugin(self, key):
        """load and return a single plugin"""
        val = self[key]
        if isinstance(val, PluginEntry):
            val.name = key # overwrite obj name attribute
            return val.get()
        else:
            return val

    def to_dict(self):
        """return a standard dict with all plugins loaded"""
        return {k: self.get_plugin(k) for k in self.keys()}
