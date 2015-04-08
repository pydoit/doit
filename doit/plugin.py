import importlib

class PluginEntry(object):
    """A Plugin entry point

    The entry-point is not loaded/imported on creation.
    Use the method `get()` to import the module and get the attribute.
    """

    class Sentinel(object):
        pass

    # indicate the entry-point object is not loaded yet
    NOT_LOADED = Sentinel()

    def __init__(self, category, name, location):
        """
        :param category str: plugin category name
        :param name str: plugin name (as used by doit)
        :param location str: python object location as <module>:<attr>
        """
        self.obj = self.NOT_LOADED
        self.category = category
        self.name = name
        self.location = location

    def __repr__(self):
        return "PluginEntry('{}', '{}', '{}')".format(
            self.category, self.name, self.location)

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

    def add_plugins(self, cfg_parser, section):
        """read all items from a ConfigParser section containing plugins"""
        # plugins from INI file
        if section in cfg_parser:
            for name, location in cfg_parser[section].items():
                self[name] = PluginEntry(section, name, location)

        # plugins from pkg_resources
        try:
            import pkg_resources
            group = "doit.{}".format(section)
            for point in pkg_resources.iter_entry_points(group=group):
                name = point.name
                location = "{}:{}".format(point.module_name, point.attrs[0])
                self[name] = PluginEntry(section, name, location)
        except ImportError: # pragma: no cover
            pass  # ignore, if setuptools is not installed


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
