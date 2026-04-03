from pathlib import Path


def test_http_layer_does_not_mutate_dotenv_files():
    violations: list[str] = []

    for path in Path("app/api").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if ".env" not in text:
            continue
        if "write_text(" in text or "os.environ[" in text:
            violations.append(str(path))

    assert violations == []
