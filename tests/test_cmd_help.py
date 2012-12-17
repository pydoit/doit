from doit.doit_cmd import DoitMain


def cmd_main(args):
    return DoitMain().run(args)

class TestHelp(object):
    def test_help_usage(self, capsys):
        cmd_main(["help"])
        out, err = capsys.readouterr()
        assert "doit list" in out

    def test_help_task_params(self, capsys):
        cmd_main(["help", "task"])
        out, err = capsys.readouterr()
        assert "Task Dictionary parameters" in out

    def test_help_cmd(self, capsys):
        cmd_main(["help", "list"])
        out, err = capsys.readouterr()
        assert "Purpose: list tasks from dodo file" in out

    def test_help_task_name(self, capsys, restore_cwd):
        cmd_main(["help", "-f", "tests/loader_sample.py", "xxx1"])
        out, err = capsys.readouterr()
        assert "xxx1" in out # name
        assert "task doc" in out # doc
        assert "" in out # params

    def test_help_wrong_name(self, capsys):
        cmd_main(["help", "wrong_name"])
        out, err = capsys.readouterr()
        assert "doit list" in out

    def test_help_no_dodo_file(self, capsys):
        cmd_main(["help", "-f", "no_dodo", "wrong_name"])
        out, err = capsys.readouterr()
        assert "doit list" in out

