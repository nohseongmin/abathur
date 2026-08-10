"""abathur CLI — 규칙 실측(bench)과 토큰 세기(count)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bench
from .tokenizer import DEFAULT_ANTHROPIC_MODEL, DEFAULT_ENCODING, build_counter

#: CLI가 한 번에 읽는 파일 크기 상한. 토큰 세기는 메모리에 전부 올리므로 제한한다.
MAX_FILE_BYTES = 2_000_000

#: 백만 토큰당 가격. 모델·시점마다 달라지고 자주 바뀌므로 기본값을 두지 않는다.
PRICE_ARG_HELP = (
    "백만 토큰당 가격(USD). 지정하면 비용 환산을 함께 출력한다. "
    "가격은 모델·시점마다 다르므로 직접 넣는다."
)


class CliError(Exception):
    """사용자에게 그대로 보여줄 실패 사유. 스택트레이스는 노출하지 않는다."""


def read_source(path_arg: str) -> str:
    if path_arg == "-":
        return sys.stdin.read()
    path = Path(path_arg).resolve()
    if not path.is_file():
        raise CliError(f"파일이 없습니다: {path_arg}")
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise CliError(
            f"파일이 너무 큽니다 ({size:,} bytes, 상한 {MAX_FILE_BYTES:,}). "
            "일부만 잘라서 넣으세요."
        )
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise CliError(f"UTF-8로 읽을 수 없는 파일입니다: {path_arg}") from None


def cmd_bench(args: argparse.Namespace) -> int:
    counter = build_counter(
        args.encoding, use_anthropic=args.anthropic, model=args.model
    )
    report = bench.run(counter)
    if args.format == "json":
        print(json.dumps(bench.to_dict(report), ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        print(bench.render_markdown(report))
    else:
        print(bench.render_text(report))
    return 0


def cmd_count(args: argparse.Namespace) -> int:
    counter = build_counter(
        args.encoding, use_anthropic=args.anthropic, model=args.model
    )
    text = read_source(args.path)
    tokens = counter.count(text)
    print(f"{tokens} 토큰 ({counter.name}, {len(text)}자)")
    if args.price_per_mtok is not None:
        cost = tokens / 1_000_000 * args.price_per_mtok
        print(f"비용 환산: ${cost:.4f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="abathur",
        description="한국어 출력 토큰 절감 규칙을 실측하고 검증한다.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--encoding", default=DEFAULT_ENCODING,
                       help=f"tiktoken 인코딩 (기본: {DEFAULT_ENCODING})")
        p.add_argument("--anthropic", action="store_true",
                       help="실제 Claude 토큰 수를 잰다. 텍스트가 Anthropic API로 전송된다")
        p.add_argument("--model", default=DEFAULT_ANTHROPIC_MODEL,
                       help=f"--anthropic 사용 시 모델 (기본: {DEFAULT_ANTHROPIC_MODEL})")

    p_bench = sub.add_parser("bench", help="규칙 코퍼스 전체를 실측한다")
    add_common(p_bench)
    p_bench.add_argument("--format", choices=("text", "markdown", "json"),
                         default="text")
    p_bench.set_defaults(func=cmd_bench)

    p_count = sub.add_parser("count", help="파일 또는 표준입력의 토큰 수를 센다")
    add_common(p_count)
    p_count.add_argument("path", help="파일 경로, 또는 표준입력은 -")
    p_count.add_argument("--price-per-mtok", type=float, default=None,
                         help=PRICE_ARG_HELP)
    p_count.set_defaults(func=cmd_count)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (CliError, RuntimeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
