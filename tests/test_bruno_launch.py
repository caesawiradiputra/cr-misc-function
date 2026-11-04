"""Task 3b: the LOCAL base URL from the VS Code launch settings."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_loader import load  # noqa: E402

PLACEHOLDER = "http://localhost:<port>"


@pytest.fixture()
def launch():
    return load("bruno_launch")


def write(root: Path, text: str) -> Path:
    (root / ".vscode").mkdir(parents=True, exist_ok=True)
    path = root / ".vscode" / "launch.json"
    path.write_text(text, encoding="utf-8")
    return root


def config(**fields: object) -> str:
    import json

    base = {"name": "API", "type": "debugpy", "request": "launch"}
    return json.dumps(
        {"version": "0.2.0", "configurations": [{**base, **fields}]}, indent=2
    )


def test_uvicorn_host_and_port_args(launch, tmp_path):
    root = write(
        tmp_path,
        config(
            module="uvicorn",
            args=["app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        ),
    )
    result = launch.local_base_url(root)
    assert result.url == "http://localhost:8000"
    assert result.source.file == ".vscode/launch.json" and result.source.line == 5


def test_hypercorn_bind(launch, tmp_path):
    root = write(
        tmp_path,
        config(module="hypercorn", args=["app.main:app", "--bind", "0.0.0.0:5000"]),
    )
    assert launch.local_base_url(root).url == "http://localhost:5000"


def test_python_module_with_port_in_env(launch, tmp_path):
    secret = "fake-launch-" + "secret-xyz"
    root = write(
        tmp_path, config(module="app.main", env={"PORT": "7001", "API_KEY": secret})
    )
    result = launch.local_base_url(root)
    assert result.url == "http://localhost:7001"
    assert secret not in repr(result)


def test_jsonc_comments_and_trailing_commas_parse(launch, tmp_path):
    text = """{
  // the launch file
  "version": "0.2.0",
  "configurations": [
    {
      "name": "API", /* inline */
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--port", "8123", "--root-path", "http://x/y",],
    },
  ],
}
"""
    assert launch.local_base_url(write(tmp_path, text)).url == "http://localhost:8123"


def test_https_only_with_ssl_option(launch, tmp_path):
    root = write(
        tmp_path,
        config(
            module="uvicorn",
            args=["app.main:app", "--port", "8443", "--ssl-keyfile", "k.pem"],
        ),
    )
    assert launch.local_base_url(root).url == "https://localhost:8443"


def test_default_port_is_assumed_and_noted(launch, tmp_path):
    root = write(tmp_path, config(module="uvicorn", args=["app.main:app"]))
    result = launch.local_base_url(root)
    assert result.url == "http://localhost:8000"
    assert any("default port" in n for n in result.notes)
    fastapi = write(
        tmp_path / "f", config(module="fastapi", args=["dev", "app/main.py"])
    )
    assert launch.local_base_url(fastapi).url == "http://localhost:8000"


def test_unknown_port_gives_placeholder_and_note(launch, tmp_path):
    root = write(tmp_path, config(module="app.main"))
    result = launch.local_base_url(root)
    assert result.url == PLACEHOLDER and any("port" in n for n in result.notes)


def test_no_launch_file_gives_placeholder_and_note(launch, tmp_path):
    result = launch.local_base_url(tmp_path)
    assert result.url == PLACEHOLDER and result.source is None
    assert any("launch.json" in n for n in result.notes)


def test_first_matching_configuration_used_and_others_listed(launch, tmp_path):
    import json

    cfgs = [
        {
            "name": "Tests",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": ["-q"],
        },
        {
            "name": "API",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": ["app.main:app", "--port", "8000"],
        },
        {
            "name": "API alt",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": ["app.main:app", "--port", "9000"],
        },
    ]
    root = write(tmp_path, json.dumps({"configurations": cfgs}))
    result = launch.local_base_url(root)
    assert result.url == "http://localhost:8000"
    assert any("API alt" in n for n in result.notes)
    assert not any("Tests" in n for n in result.notes)


def test_env_file_never_read_and_other_env_values_never_copied(
    launch, tmp_path, monkeypatch
):
    marker = "fake-env-file-" + "marker-123"
    (tmp_path / ".env").write_text(f"TOKEN={marker}\n", encoding="utf-8")
    root = write(
        tmp_path,
        config(
            module="uvicorn",
            args=["app.main:app", "--port", "8000"],
            envFile="${workspaceFolder}/.env",
            env={"DB_PASSWORD": marker},
        ),
    )
    opened: list[str] = []
    original = Path.read_text

    def spy(self, *args, **kwargs):
        opened.append(self.name)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    result = launch.local_base_url(root)
    assert opened == ["launch.json"]
    assert marker not in repr(result)


def test_broken_json_gives_placeholder_and_note_not_a_crash(launch, tmp_path):
    result = launch.local_base_url(write(tmp_path, '{"configurations": [ {'))
    assert result.url == PLACEHOLDER
    assert any("could not be read" in n for n in result.notes)
