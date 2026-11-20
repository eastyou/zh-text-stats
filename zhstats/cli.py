"""zhstats 命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Sequence

from zhstats.stats import (
    DEFAULT_READING_CPM,
    DEFAULT_READING_WPM,
    TextStats,
    analyze,
)

STDIN_NAME = "<stdin>"


class InputError(Exception):
    """输入无法读取时抛出，便于命令行给出统一提示。"""


def read_text(path: str) -> str:
    """按 UTF-8（允许 BOM）读取文件；``-`` 表示标准输入。"""
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return handle.read()
    except FileNotFoundError as exc:
        raise InputError("文件不存在: {0}".format(path)) from exc
    except IsADirectoryError as exc:
        raise InputError("这是一个目录，不是文件: {0}".format(path)) from exc
    except PermissionError as exc:
        raise InputError("没有权限读取: {0}".format(path)) from exc
    except UnicodeDecodeError as exc:
        raise InputError("文件不是有效的 UTF-8 文本: {0}".format(path)) from exc
    except OSError as exc:
        raise InputError(
            "读取文件失败: {0} ({1})".format(path, exc.strerror or exc)
        ) from exc


def _format_stats(name: str, stats: TextStats) -> str:
    keywords = "、".join("{0}({1})".format(word, count) for word, count in stats.keywords)
    rows = [
        ("总字符", str(stats.characters)),
        ("汉字", str(stats.chinese_characters)),
        ("英文单词", str(stats.latin_words)),
        ("数字字符", str(stats.digits)),
        ("空白字符", str(stats.whitespace)),
        ("标点符号", str(stats.punctuation)),
        ("自然段", str(stats.paragraphs)),
        ("句子", str(stats.sentences)),
        ("计入字数", str(stats.words)),
        ("预计阅读", "{0:.1f} 分钟".format(stats.reading_minutes)),
        ("高频词", keywords or "（无）"),
    ]
    width = max(len(label) for label, _ in rows)
    lines: List[str] = ["文件: {0}".format(name)]
    for label, value in rows:
        lines.append("  {0}  {1}".format(label.ljust(width), value))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zhstats",
        description="统计中文文本的字数、标点、段落与预计阅读时长。",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="待统计的文件；使用 - 表示标准输入",
    )
    parser.add_argument(
        "--stdin", action="store_true", help="从标准输入读取（等价于文件参数 -）"
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="以 JSON 格式输出，便于脚本处理"
    )
    parser.add_argument(
        "-n", "--top", type=int, default=10, metavar="N",
        help="高频词数量，0 表示关闭（默认 10）",
    )
    parser.add_argument(
        "--min-count", type=int, default=2, metavar="N",
        help="高频词的最小出现次数（默认 2）",
    )
    parser.add_argument(
        "--cpm", type=float, default=DEFAULT_READING_CPM, metavar="N",
        help="中文阅读速度，字/分钟（默认 400）",
    )
    parser.add_argument(
        "--wpm", type=float, default=DEFAULT_READING_WPM, metavar="N",
        help="英文阅读速度，词/分钟（默认 220）",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.top < 0:
        parser.error("--top 不能为负数")
    if args.min_count < 1:
        parser.error("--min-count 至少为 1")
    if args.cpm <= 0 or args.wpm <= 0:
        parser.error("阅读速度必须大于 0")

    targets = list(args.files)
    if args.stdin and targets:
        parser.error("--stdin 不能与文件参数同时使用")
    if args.stdin:
        targets = ["-"]
    if not targets:
        parser.print_usage(sys.stderr)
        print("错误: 请至少指定一个文件，或使用 --stdin", file=sys.stderr)
        return 2

    results: List[dict] = []
    failed = False
    for path in targets:
        try:
            text = read_text(path)
        except InputError as exc:
            print("错误: {0}".format(exc), file=sys.stderr)
            failed = True
            continue
        stats = analyze(
            text,
            top_keywords=args.top,
            min_keyword_count=args.min_count,
            chars_per_minute=args.cpm,
            words_per_minute=args.wpm,
        )
        name = STDIN_NAME if path == "-" else path
        results.append({"file": name, "stats": stats})
        if not args.json:
            if len(results) > 1:
                print()
            print(_format_stats(name, stats))

    if args.json and results:
        payload = [
            {"file": item["file"], **item["stats"].to_dict()} for item in results
        ]
        if len(payload) == 1:
            print(json.dumps(payload[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 2 if failed else 0
