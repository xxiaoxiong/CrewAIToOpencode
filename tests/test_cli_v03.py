from src import cli


def test_capabilities_command_runs(capsys):
    code = cli.main(["--project", "demo-project", "--capabilities"])
    output = capsys.readouterr().out

    assert code == 0
    assert "personal local" in output
    assert "quick" in output
    assert "full" in output


def test_doctor_command_runs_with_stubbed_opencode(monkeypatch, capsys):
    monkeypatch.setattr(cli, "check_opencode", lambda project_id: 0)

    code = cli.main(["--project", "demo-project", "--doctor"])
    output = capsys.readouterr().out

    assert code == 0
    assert "config ok" in output
    assert "crewai ok" in output
