"""中文文本统计的核心实现，只依赖标准库。"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Tuple

_CJK_RANGE = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_CJK_RE = re.compile("[" + _CJK_RANGE + "]")
_CJK_RUN_RE = re.compile("[" + _CJK_RANGE + "]+")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")
_DIGIT_RE = re.compile(r"[0-9]")
_WHITESPACE_RE = re.compile(r"\s")
_SENTENCE_END_RE = re.compile(r"[。！？!?…]")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n[ \t\r]*\n")

# 高频词统计时过滤掉的虚词与常见搭配，避免结果里全是"我们""可以"这类词。
_STOP_CHARS = frozenset(
    "的了着过是在有和与及或就都也还很太最更没不无我你他她它这那什么怎吗呢吧啊呀哦嗯"
    "把被让给对从向往以于为而则其之者"
)
_STOP_BIGRAMS = frozenset(
    {
        "我们", "你们", "他们", "她们", "它们", "这个", "那个", "这些", "那些",
        "这样", "那样", "一个", "一些", "一种", "没有", "可以", "自己", "什么",
        "就是", "不是", "如果", "因为", "所以", "但是", "而且", "以及", "已经",
        "还是", "时候", "现在", "然后", "还有", "只是", "不过", "之后", "之前",
        "通过", "进行", "对于", "关于", "其中", "能够", "需要", "应该", "可能",
        "并且", "或者", "虽然", "然而", "因此", "于是", "一样", "非常", "比较",
    }
)

DEFAULT_READING_CPM = 400.0
DEFAULT_READING_WPM = 220.0


@dataclass(frozen=True)
class TextStats:
    """一段文本的统计结果。"""

    characters: int
    chinese_characters: int
    latin_words: int
    words: int
    digits: int
    whitespace: int
    punctuation: int
    paragraphs: int
    sentences: int
    reading_minutes: float
    keywords: Tuple[Tuple[str, int], ...] = ()

    def to_dict(self) -> Dict[str, object]:
        """转换为可直接 JSON 序列化的字典。"""
        return {
            "characters": self.characters,
            "chinese_characters": self.chinese_characters,
            "latin_words": self.latin_words,
            "words": self.words,
            "digits": self.digits,
            "whitespace": self.whitespace,
            "punctuation": self.punctuation,
            "paragraphs": self.paragraphs,
            "sentences": self.sentences,
            "reading_minutes": self.reading_minutes,
            "keywords": [
                {"word": word, "count": count} for word, count in self.keywords
            ],
        }


def analyze(
    text: str,
    top_keywords: int = 10,
    min_keyword_count: int = 2,
    chars_per_minute: float = DEFAULT_READING_CPM,
    words_per_minute: float = DEFAULT_READING_WPM,
) -> TextStats:
    """统计一段文本。

    Args:
        text: 待统计的文本。
        top_keywords: 返回多少个高频词，0 表示不统计。
        min_keyword_count: 高频词至少出现多少次。
        chars_per_minute: 中文阅读速度（字/分钟），必须大于 0。
        words_per_minute: 英文阅读速度（词/分钟），必须大于 0。

    Raises:
        TypeError: text 不是字符串。
        ValueError: 参数越界。
    """
    if not isinstance(text, str):
        raise TypeError("text 必须是 str")
    if top_keywords < 0:
        raise ValueError("top_keywords 不能为负数")
    if min_keyword_count < 1:
        raise ValueError("min_keyword_count 至少为 1")
    if chars_per_minute <= 0:
        raise ValueError("chars_per_minute 必须大于 0")
    if words_per_minute <= 0:
        raise ValueError("words_per_minute 必须大于 0")

    chinese_characters = len(_CJK_RE.findall(text))
    latin_words = len(_LATIN_WORD_RE.findall(text))
    reading_minutes = round(
        chinese_characters / chars_per_minute + latin_words / words_per_minute, 1
    )
    keywords = (
        _top_keywords(text, top_keywords, min_keyword_count) if top_keywords else ()
    )
    return TextStats(
        characters=len(text),
        chinese_characters=chinese_characters,
        latin_words=latin_words,
        words=chinese_characters + latin_words,
        digits=len(_DIGIT_RE.findall(text)),
        whitespace=len(_WHITESPACE_RE.findall(text)),
        punctuation=sum(1 for char in text if _is_punctuation(char)),
        paragraphs=_count_paragraphs(text),
        sentences=_count_sentences(text),
        reading_minutes=reading_minutes,
        keywords=keywords,
    )


def _is_punctuation(char: str) -> bool:
    return unicodedata.category(char).startswith("P")


def _count_paragraphs(text: str) -> int:
    return sum(1 for block in _PARAGRAPH_SPLIT_RE.split(text) if block.strip())


def _count_sentences(text: str) -> int:
    count = len(_SENTENCE_END_RE.findall(text))
    if count:
        return count
    return 1 if text.strip() else 0


def _top_keywords(
    text: str, limit: int, min_count: int
) -> Tuple[Tuple[str, int], ...]:
    """用相邻汉字二元组粗略提取高频词。"""
    counts: Dict[str, int] = {}
    for run in _CJK_RUN_RE.findall(text):
        for index in range(len(run) - 1):
            gram = run[index : index + 2]
            if gram in _STOP_BIGRAMS:
                continue
            if any(char in _STOP_CHARS for char in gram):
                continue
            counts[gram] = counts.get(gram, 0) + 1

    ranked = sorted(
        ((word, count) for word, count in counts.items() if count >= min_count),
        key=lambda item: (-item[1], item[0]),
    )
    return tuple(ranked[:limit])
