"""zhstats 的单元测试。"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from zhstats.cli import InputError, main, read_text
from zhstats.stats import analyze


class AnalyzeTests(unittest.TestCase):
    def test_empty_text(self):
        stats = analyze("")
        self.assertEqual(stats.characters, 0)
        self.assertEqual(stats.words, 0)
        self.assertEqual(stats.paragraphs, 0)
        self.assertEqual(stats.sentences, 0)
        self.assertEqual(stats.reading_minutes, 0.0)
        self.assertEqual(stats.keywords, ())

    def test_mixed_text(self):
        text = "学习 Python 3 天，收获很大！\n\n第二段。"
        stats = analyze(text)
        self.assertEqual(stats.characters, len(text))
        self.assertEqual(stats.chinese_characters, 10)
        self.assertEqual(stats.latin_words, 1)
        self.assertEqual(stats.digits, 1)
        self.assertEqual(stats.whitespace, 5)
        self.assertEqual(stats.punctuation, 3)
        self.assertEqual(stats.paragraphs, 2)
        self.assertEqual(stats.sentences, 2)
        self.assertEqual(stats.words, 11)

    def test_counts_sentence_without_punctuation(self):
        self.assertEqual(analyze("没有标点的一句话").sentences, 1)

    def test_keywords_are_ranked(self):
        text = "人工智能改变生活，人工智能改变学习，人工智能很重要。"
        stats = analyze(text, top_keywords=5)
        self.assertEqual(stats.keywords[0][0], "人工")
        self.assertGreaterEqual(stats.keywords[0][1], 3)

    def test_keywords_filtered_by_min_count(self):
        stats = analyze("数学学习，数学练习。", top_keywords=10, min_keyword_count=5)
        self.assertEqual(stats.keywords, ())

    def test_keywords_can_be_disabled(self):
        self.assertEqual(analyze("人工智能人工智能", top_keywords=0).keywords, ())

    def test_reading_speed_changes_result(self):
        text = "字" * 400
        fast = analyze(text, chars_per_minute=400)
        slow = analyze(text, chars_per_minute=200)
        self.assertEqual(fast.reading_minutes, 1.0)
        self.assertEqual(slow.reading_minutes, 2.0)

    def test_invalid_arguments_raise(self):
        with self.assertRaises(TypeError):
            analyze(None)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            analyze("文本", top_keywords=-1)
        with self.assertRaises(ValueError):
            analyze("文本", min_keyword_count=0)
        with self.assertRaises(ValueError):
            analyze("文本", chars_per_minute=0)
        with self.assertRaises(ValueError):
            analyze("文本", words_per_minute=0)


class ReadTextTests(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(InputError):
            read_text("/definitely/not/here.txt")

    def test_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InputError):
                read_text(tmp)

    def test_non_utf8_file_is_rejected(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"\xff\xfe\x00\x01")
            path = handle.name
        try:
            with self.assertRaises(InputError):
                read_text(path)
        finally:
            os.unlink(path)

    def test_utf8_bom_is_accepted(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write("\ufeff你好".encode("utf-8"))
            path = handle.name
        try:
            self.assertEqual(read_text(path), "你好")
        finally:
            os.unlink(path)


class CliTests(unittest.TestCase):
    def _run(self, argv, stdin_text=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdin = sys.stdin
        if stdin_text is not None:
            sys.stdin = io.StringIO(stdin_text)
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(argv)
        finally:
            sys.stdin = old_stdin
        return code, stdout.getvalue(), stderr.getvalue()

    def test_reports_missing_file(self):
        code, _, err = self._run(["no-such-file.txt"])
        self.assertEqual(code, 2)
        self.assertIn("文件不存在", err)

    def test_reads_stdin(self):
        code, out, _ = self._run(["--stdin"], stdin_text="你好世界。")
        self.assertEqual(code, 0)
        self.assertIn("汉字", out)
        self.assertIn("4", out)

    def test_json_output(self):
        code, out, _ = self._run(["--stdin", "--json"], stdin_text="你好世界。")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["chinese_characters"], 4)
        self.assertIn("keywords", payload)

    def test_multiple_files_return_json_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = os.path.join(tmp, "a.txt")
            second = os.path.join(tmp, "b.txt")
            for path, content in ((first, "你好。"), (second, "世界。")):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
            code, out, _ = self._run([first, second, "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 2)

    def test_requires_input(self):
        code, _, err = self._run([])
        self.assertEqual(code, 2)
        self.assertIn("请至少指定一个文件", err)

    def test_invalid_top_argument(self):
        with self.assertRaises(SystemExit):
            self._run(["--stdin", "--top", "-1"])


if __name__ == "__main__":
    unittest.main()
