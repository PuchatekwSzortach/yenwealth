"""
Keep the front-page example in README.md synchronized with its Python source.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
EXAMPLE_PATH = ROOT / "examples/front_page.py"
START_MARKER = "<!-- front_page_example:start -->"
END_MARKER = "<!-- front_page_example:end -->"


def render_readme(readme_content: str, example_source: str) -> str:
    if readme_content.count(START_MARKER) != 1 or readme_content.count(END_MARKER) != 1:
        raise ValueError("README.md must contain each front-page example marker exactly once")

    start = readme_content.index(START_MARKER) + len(START_MARKER)
    end = readme_content.index(END_MARKER)
    if end < start:
        raise ValueError("README.md front-page example markers are in the wrong order")

    example_source = example_source.rstrip("\n")
    generated_block = f"\n```python\n{example_source}\n```\n"
    return readme_content[:start] + generated_block + readme_content[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync front-page example into README.md")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if README.md does not contain the current example source",
    )
    arguments = parser.parse_args()

    readme_content = README_PATH.read_text(encoding="utf-8")
    example_source = EXAMPLE_PATH.read_text(encoding="utf-8")
    updated_readme = render_readme(readme_content, example_source)

    if arguments.check:
        if updated_readme != readme_content:
            print(
                "README.md front-page example is stale; "
                "run python scripts/sync_front_page_example.py",
                file=sys.stderr,
            )
            return 1
        return 0

    README_PATH.write_text(updated_readme, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
