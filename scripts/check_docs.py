"""외부 접속 없이 Markdown의 로컬 링크·heading anchor를 검사한다."""

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "node_modules", ".pytest_cache", ".ruff_cache"}


def prose(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return re.sub(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[^\n]*$", "", text)


def main() -> int:
    errors: list[str] = []
    documents = [
        path
        for path in ROOT.rglob("*.md")
        if not EXCLUDED.intersection(path.relative_to(ROOT).parts)
    ]
    for path in documents:
        for target in re.findall(r"!?\[[^\]\n]*\]\(([^\n]+?)\)", prose(path)):
            target = target.strip().split(' "', 1)[0].strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            destination = (
                ROOT / unquote(url.path.lstrip("/"))
                if url.path.startswith("/")
                else path.parent / unquote(url.path)
                if url.path
                else path
            )
            if not destination.exists():
                errors.append(f"{path.relative_to(ROOT)}: 없는 링크 {target}")
            elif destination.suffix == ".md" and url.fragment:
                anchors = {
                    re.sub(r"\s", "-", re.sub(r"[^\w\-\s]", "", heading.lower()))
                    for heading in re.findall(
                        r"^#{1,6}\s+(.+?)\s*$", prose(destination), re.MULTILINE
                    )
                }
                if unquote(url.fragment) not in anchors:
                    errors.append(f"{path.relative_to(ROOT)}: 없는 anchor {target}")
    for error in errors:
        print(error, file=sys.stderr)
    print(f"로컬 문서 검사: {len(documents)}개, 오류 {len(errors)}개")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
