from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime_v2.provider_adapter import LocalTextFileProviderAdapter
from runtime_v2.vertical_slice import RuntimeV2Service, SQLiteRuntimeV2Repository, parse_create_text_file


DEFAULT_PROMPT = "создай файл runtime_v2_real.txt точно RUNTIME_V2_REAL_OK"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Запустить ограниченный тестовый срез Runtime V2.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Команда на создание тестового файла.")
    parser.add_argument("--workspace", default=str(PROJECT_ROOT / ".tmp_runtime_v2_smoke"), help="Папка тестового запуска.")
    parser.add_argument("--database", default="", help="Путь к SQLite. По умолчанию <workspace>/runtime_v2.sqlite3.")
    parser.add_argument("--crash-after-effect", action="store_true", help="Сымитировать сбой после записи файла и проверить восстановление.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(args.workspace).resolve()
    database = Path(args.database).resolve() if args.database else workspace / "runtime_v2.sqlite3"
    request = parse_create_text_file(args.prompt)
    if request is None:
        print(json.dumps({"ok": False, "error": "prompt_not_supported"}, ensure_ascii=False, indent=2))
        return 2

    repository = SQLiteRuntimeV2Repository(database)
    service = RuntimeV2Service(repository, workspace)
    adapter = LocalTextFileProviderAdapter()
    state = service.create_task(request, "agent-runtime-v2-test", "org-runtime-v2-test", adapter.provider_id)
    statuses: list[str] = []

    try:
        result = service.execute(
            state.runtime_task_id,
            request,
            adapter,
            on_status=statuses.append,
            crash_after_effect=args.crash_after_effect,
        )
    except RuntimeError as exc:
        if str(exc) != "SIMULATED_CRASH_AFTER_EFFECT":
            raise
        result = service.recover(state.runtime_task_id, request)

    output = result.to_dict()
    output["database"] = str(database)
    output["workspace"] = str(workspace)
    output["statuses"] = statuses
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if result.ok and result.content_exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
