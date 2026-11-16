"""Validate the portable Codex package without connecting external services."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    agents = sorted((ROOT / ".codex/agents").glob("*.toml"))
    assert len(agents) == 9, "Expected nine Codex agent profiles"
    for path in agents:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert data["name"] == path.stem, f"Agent name mismatch: {path.name}"
        assert data.get("description") and data.get("developer_instructions"), path.name
    tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
    hook = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
    command = hook["hooks"]["PreToolUse"][0]["hooks"][0]
    assert command["command"] == command["commandWindows"]
    assert "C:" not in command["commandWindows"], "Hook contains a machine-specific path"
    for name in ("ux-review", "llama-funnel-studio"):
        text = (ROOT / f".agents/skills/{name}/SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"Skill has no frontmatter: {name}"
        assert f"name: {name}\n" in text, f"Skill name mismatch: {name}"
    studio = ROOT / "systems/llama-funnel-studio"
    for rel in ("AGENTS.md", "README.md", "CONTRATO.md", "especialistas/EQUIPOS.md"):
        assert (studio / rel).is_file(), f"Missing Studio contract: {rel}"
    scripts = [*studio.rglob("*.py"), Path(__file__).resolve()]
    for path in scripts:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    registry = ast.parse((studio / "agente_mejora/mejoras.py").read_text(encoding="utf-8"))
    assignments = [node for node in registry.body if isinstance(node, ast.AnnAssign)]
    records = next(node.value for node in assignments if getattr(node.target, "id", "") == "REGISTRO")
    assert ast.literal_eval(records) == [], "Private improvement history must stay outside the export"
    roots = [ROOT / ".codex", ROOT / "CodexMemory", studio]
    forbidden = {".env", "token.json", "credentials.json", "prod-db.json"}
    extensions = {".db", ".sqlite", ".sqlite3", ".pem", ".crt", ".key", ".exe", ".dll", ".zip", ".xlsx"}
    for folder in roots:
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            assert path.name not in forbidden and path.suffix.lower() not in extensions, str(path.relative_to(ROOT))
            assert not any(part in {"node_modules", ".venv", "__pycache__"} for part in path.parts), str(path)
            text = path.read_text(encoding="utf-8")
            assert "C:\\Users\\User" not in text and "C:/Users/User" not in text, str(path.relative_to(ROOT))
    assert (ROOT / "VERSION").read_text().strip() == "2.0.0"
    print(f"PASS: {len(agents)} agents, two native skills, portable hooks, {len(scripts)} Python files, clean export boundaries")


if __name__ == "__main__":
    main()
