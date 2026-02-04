from __future__ import annotations

from pathlib import Path
import mkdocs_gen_files

PKG_DIR = Path("msight_core")

EXCLUDE_DIRS = {"tests", "test", "scripts", "examples", "benchmark", "benchmarks"}
EXCLUDE_PREFIXES = ("_",)

def excluded(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    if path.suffix == ".py" and path.stem.startswith(EXCLUDE_PREFIXES) and path.name != "__init__.py":
        return True
    return False

nav = mkdocs_gen_files.Nav()

for py in sorted(PKG_DIR.rglob("*.py")):
    if excluded(py):
        continue
    if py.name == "__init__.py":
        rel_pkg = py.parent.relative_to(PKG_DIR.parent)     # Path('msight_core/data')
        mod = ".".join(rel_pkg.parts)                       # 'msight_core.data'

        # Folder index page for the package
        doc_path = (Path("reference") / rel_pkg) / "index.md"  # reference/msight_core/data/index.md
        # IMPORTANT: use tuple keys
        nav[tuple(rel_pkg.parts)] = doc_path.as_posix()

        with mkdocs_gen_files.open(doc_path, "w") as f:
            f.write(f"# `{mod}`\n\n::: {mod}\n")

        # OPTIONAL but recommended: avoid shadowing by removing any old flat page name
        # (Don't generate reference/msight_core/data.md at all.)
        continue

    rel_mod = py.relative_to(PKG_DIR.parent).with_suffix("")  # Path('msight_core/data/bytes')
    mod = ".".join(rel_mod.parts)                             # 'msight_core.data.bytes'
    if mod.endswith(".__main__"):
        continue

    doc_path = Path("reference") / rel_mod.with_suffix(".md") # reference/msight_core/data/bytes.md
    nav[tuple(rel_mod.parts)] = doc_path.as_posix()

    with mkdocs_gen_files.open(doc_path, "w") as f:
        f.write(f"# `{mod}`\n\n::: {mod}\n")

with mkdocs_gen_files.open("SUMMARY.md", "w") as f:
    f.write("* [Home](index.md)\n")
    f.writelines(nav.build_literate_nav())
