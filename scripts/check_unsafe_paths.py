"""Fail on unsafe Python deserializers; do not import application code."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect(source, filename):
    tree = ast.parse(source, filename=filename)
    aliases = {}
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update({item.asname or item.name: item.name for item in node.names})
        elif isinstance(node, ast.ImportFrom):
            aliases.update({item.asname or item.name: f"{node.module}.{item.name}" for item in node.names})
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        head, *tail = name.split(".")
        name = ".".join([aliases.get(head, head), *tail])
        unsafe = name in {"pickle.load", "pickle.loads", "joblib.load", "yaml.load", "dill.load", "dill.loads"}
        if name == "torch.load":
            unsafe = not any(
                k.arg == "weights_only" and isinstance(k.value, ast.Constant) and k.value.value is True
                for k in node.keywords
            )
        if unsafe:
            findings.append({"file": filename, "line": node.lineno, "call": name})
    return findings


def main():
    paths = sorted(
        [
            p
            for directory in ("ml_service", "scripts")
            for p in (ROOT / directory).rglob("*.py")
            if "__pycache__" not in p.parts
        ]
    )
    findings = [
        row for path in paths for row in inspect(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix())
    ]
    report = {
        "scope": "Python source deserialization call gate; not a complete static security analyzer",
        "files_checked": len(paths),
        "findings": findings,
    }
    (ROOT / "reports/unsafe-paths.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
