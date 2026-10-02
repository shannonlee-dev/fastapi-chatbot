"""실제 Jinja2 화면을 임시 파일로 rendering한 뒤 DOM 동작을 검사한다."""

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from app.ui.templating import templates

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    with TemporaryDirectory(prefix="chat-ui-tests-") as directory:
        html = Path(directory) / "chat.html"
        html.write_text(
            templates.get_template("chat.html").render(
                chat_exchanges=[], is_admin=False
            ),
            encoding="utf-8",
        )
        environment = dict(os.environ, CHAT_TEST_HTML=str(html))
        return subprocess.run(
            ["node", str(ROOT / "tests/browser/chat.test.cjs")],
            cwd=ROOT,
            env=environment,
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
