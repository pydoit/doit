from doit.doit_cmd import DoitMain


def cmd_main(args, extra_config=None):
    if extra_config:
        extra_config = {'GLOBAL': extra_config}
    return DoitMain(extra_config=extra_config).run(args)

class TestHelp(object):
    def test_help_usage(self, capsys):
        cmd_main(["help"])
        out, err = capsys.readouterr()
        assert "doit list" in out

    def test_help_plugin_name(self, capsys):
        plugin = {'XXX': 'tests.sample_plugin:MyCmd'}
        DoitMain(extra_config={'COMMAND':plugin}).run(["help"])
        out, err = capsys.readouterr()
        assert "doit XXX " in out
        assert "test extending doit commands" in out, out

    def test_help_task_params(self, capsys):
        cmd_main(["help", "task"])
        out, err = capsys.readouterr()
        assert "Task Dictionary parameters" in out

    def test_help_cmd(self, capsys):
        cmd_main(["help", "list"], {'dep_file': 'foo.db'})
        out, err = capsys.readouterr()
        assert "Purpose: list tasks from dodo file" in out
        # overwritten defaults, are shown as default
        assert "file used to save successful runs [default: foo.db]" in out

    def test_help_task_name(self, capsys, restore_cwd, depfile_name):
        cmd_main(["help", "-f", "tests/loader_sample.py",
                  "--db-file", depfile_name, "xxx1"])
        out, err = capsys.readouterr()
        assert "xxx1" in out # name
        assert "task doc" in out # doc
        assert "" in out # params

    def test_help_wrong_name(self, capsys, restore_cwd, depfile_name):
        cmd_main(["help", "-f", "tests/loader_sample.py",
                  "--db-file", depfile_name, "wrong_name"])
        out, err = capsys.readouterr()
        assert "doit list" in out

    def test_help_no_dodo_file(self, capsys):
        cmd_main(["help", "-f", "no_dodo", "wrong_name"])
        out, err = capsys.readouterr()
        assert "doit list" in out

