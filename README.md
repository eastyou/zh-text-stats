# zh-text-stats

[![CI](https://github.com/eastyou/zh-text-stats/actions/workflows/ci.yml/badge.svg)](https://github.com/eastyou/zh-text-stats/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](pyproject.toml)

中文文本统计命令行工具：一条命令看清字数、汉字数、标点、段落、句子、预计阅读时长和高频词。

写作文、做内容运营、检查文章长度时，`wc -m` 只能给出总字符数，对中文并不友好。`zhstats` 把中文写作真正关心的指标拆开统计，并支持 JSON 输出接入自动化流程。

## 特性

- **中文优先**：汉字、英文单词、数字分别统计，字数按"汉字 + 英文单词"计算
- **阅读时长估算**：中文按 400 字/分钟、英文按 220 词/分钟，可自定义
- **高频词**：基于汉字二元组统计，内置虚词过滤，避免结果全是"我们""可以"
- **零依赖**：只使用 Python 标准库，Python 3.9+ 即可运行
- **多输入**：支持多个文件、标准输入、JSON 输出
- **错误友好**：文件不存在、目录、非 UTF-8 编码都会给出明确提示并以退出码 2 结束

## 安装

```bash
pip install "git+https://github.com/eastyou/zh-text-stats.git"
```

本地开发安装：

```bash
git clone https://github.com/eastyou/zh-text-stats.git
cd zh-text-stats
python3 -m pip install -e .
```

不安装也可以直接运行：

```bash
python3 -m zhstats article.txt
```

## 使用

```console
$ zhstats article.txt
文件: article.txt
  总字符    1234
  汉字      1012
  英文单词  36
  数字字符  8
  空白字符  142
  标点符号  36
  自然段    12
  句子      48
  计入字数  1048
  预计阅读  2.7 分钟
  高频词    学习(12)、数学(9)、方法(7)
```

常用组合：

```bash
# 从标准输入读取
cat article.txt | zhstats --stdin

# JSON 输出，方便接入脚本或其他工具
zhstats article.txt --json

# 同时统计多个文件，并只显示前 5 个高频词
zhstats a.txt b.txt --top 5

# 自定义阅读速度（字/分钟）
zhstats article.txt --cpm 300
```

### 参数

| 参数 | 说明 |
| --- | --- |
| `FILE ...` | 待统计的文件，`-` 表示标准输入 |
| `--stdin` | 从标准输入读取，等价于传入 `-` |
| `-j, --json` | 输出 JSON |
| `-n, --top N` | 高频词数量，默认 10，`0` 关闭 |
| `--min-count N` | 高频词至少出现的次数，默认 2 |
| `--cpm N` | 中文阅读速度，默认 400 字/分钟 |
| `--wpm N` | 英文阅读速度，默认 220 词/分钟 |

### 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 全部文件统计成功 |
| `1` | 预留 |
| `2` | 参数错误或文件读取失败 |

## 作为库使用

```python
from zhstats import analyze

stats = analyze("今天学习了 Python，收获很大。")
print(stats.chinese_characters)  # 9
print(stats.reading_minutes)     # 0.0
print(stats.keywords)
```

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
```

CI 会在 Python 3.9 ~ 3.13 上运行全部测试。

## License

[MIT](LICENSE) © 2026 eastyou
