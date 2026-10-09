"""从 script.md 算出时间轴：每句话的起止、关键词出现的时间、字幕分段。

输出（都写在本目录 / 上一级）：
  timeline.js     给 animatic.html 用（window.TIMELINE = {...}）
  timeline.json   给 sound.py 用
  ../subtitles.srt

默认按估算语速排时间。录完旁白后，在 sentence_starts.txt 里每行写一句的开始时间（秒），
共 N 行，和稿子的句子一一对应，再跑一遍本脚本，时间轴就会贴着你的录音走。

用法：python3 timing.py
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent.parent / "script.md"
OVERRIDE = HERE / "sentence_starts.txt"

RATE = 3.6        # 每秒念几个字（约每分钟 216 字）
PAUSE = 0.6       # 每句后的气口（秒）
TAIL = 4.0        # 最后一句念完后，画面再停多久
SUB_MAX = 16      # 每条字幕最多几个字

SPOKEN = re.compile(r"[一-鿿0-9A-Za-z]")

# 关键词 → 动画在这个词开口时触发。子串必须在稿子里只出现一次。
MARKERS = {
    "s1961": "1961 年 11 月", "formula": "写了一个公式", "galaxy": "想估一估银河系里",
    "Rstar": "每年诞生的恒星", "fp": "乘上有行星的", "ne": "适合住的", "fl": "长出生命的",
    "fi": "长出智慧的", "fc": "学会发信号的", "L": "最后一项叫 L", "shrink": "每乘一项，数字就小一圈",
    "y2010": "2010 年", "nogf": "他为什么没有女朋友", "n10510": "一万零五百人",
    "x20": "乘上觉得他有魅力的", "x2": "乘上单身的", "x10": "乘上聊得来的", "n26": "最后剩下 26 个",
    "joke": "他是写着玩的",
    "yours": "换成你的公式", "births": "全国生了多少孩子", "ratio": "男孩比女孩多多少",
    "city": "你在哪座城市长大", "college": "有多少人读了大学", "these": "这些数", "multiplied": "就已经乘进去了",
    "changing": "而且它们还在变", "y2013": "2013 年", "n1347": "1347 万对", "y2025": "2025 年",
    "n676": "676 万对", "half": "十二年，少了一半", "notgood": "很多人以为", "before": "在你出生前就算好了",
    "fermi": "1950 年", "where": "那他们都在哪儿", "listen": "大家都在听", "quiet": "整片星空都很安静",
    "cityalso": "城市也一样", "singles": "几百万个单身的人", "serious": "谁先认真",
    "spoke": "可人类还是先开口了", "voyager": "1977 年", "langs": "55 种语言的问候",
    "greet1": "各位都好吧", "greet2": "我们都很想念你们", "greet3": "有空请到这儿来玩",
    "flying": "它飞了快五十年", "history": "是历史替你乘好的", "onlyL": "只有最后那个 L",
    "inhand": "一直在你手里", "nostance": "我不劝你结婚",
    "out1": "数学就算到这儿", "out2": "剩下除不尽的", "out3": "叫生活",
}

# 画面上已经有竖排大字的句子，字幕不再重复
BIG_TEXT = {"你这辈子会不会遇见那个人", "有一部分答案", "在你出生之前就写好了",
            "各位都好吧？", "我们都很想念你们", "有空请到这儿来玩",
            "数学就算到这儿", "剩下除不尽的", "叫生活", "十二年", "少了一半"}


def spoken_len(s):
    return len(SPOKEN.findall(s))


def body_sentences():
    text = SCRIPT.read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1]
    sents = []
    for para in [p.strip() for p in body.split("\n") if p.strip()]:
        sents += [s.strip() for s in re.split(r"(?<=[。？])", para) if s.strip()]
    return sents


def tidy(s):
    """字幕显示用：去掉中文和数字之间的空格，去掉句尾的逗号句号。"""
    s = re.sub(r"(?<=[一-鿿0-9A-Za-z])\s+(?=[一-鿿0-9A-Za-z])", "", s)
    return s.rstrip("，。、：；")


def chunks(sentence):
    """按标点切成小段，再把相邻小段拼到不超过 SUB_MAX 字。
    画面上已有竖排大字的小段单独成段并标记 hidden，不和别的段拼在一起。"""
    pieces = [p for p in re.split(r"(?<=[，：？。、；])", sentence) if p.strip()]
    out = []  # [text, hidden]
    for p in pieces:
        hidden = tidy(p) in BIG_TEXT or tidy(p).rstrip("？") in BIG_TEXT
        if out and not hidden and not out[-1][1] and spoken_len(out[-1][0]) + spoken_len(p) <= SUB_MAX:
            out[-1][0] += p
        else:
            out.append([p, hidden])
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    sents = body_sentences()
    starts = []
    if OVERRIDE.exists():
        starts = [float(x) for x in OVERRIDE.read_text().split() if x.strip()]
        if len(starts) != len(sents):
            raise SystemExit(f"sentence_starts.txt 有 {len(starts)} 行，稿子有 {len(sents)} 句，对不上")

    timeline, t = [], 0.0
    for i, s in enumerate(sents):
        if starts:
            t = starts[i]
        dur = spoken_len(s) / RATE
        end = (starts[i + 1] - PAUSE) if starts and i + 1 < len(starts) else t + dur
        timeline.append({"i": i, "text": s, "start": round(t, 3), "end": round(end, 3)})
        t = end + PAUSE
    total = round(timeline[-1]["end"] + TAIL, 3)

    def time_at(sub):
        hits = [(k, x) for k, x in enumerate(timeline) if sub in x["text"]]
        if len(hits) != 1:
            raise SystemExit(f"关键词「{sub}」在稿子里出现了 {len(hits)} 次，需要正好 1 次")
        k, x = hits[0]
        before = x["text"][: x["text"].index(sub)]
        span = x["end"] - x["start"]
        return round(x["start"] + span * spoken_len(before) / max(1, spoken_len(x["text"])), 3)

    markers = {name: time_at(sub) for name, sub in MARKERS.items()}

    subs = []
    for x in timeline:
        cs = chunks(x["text"])
        n_total = max(1, spoken_len(x["text"]))
        acc = 0
        for c, hidden in cs:
            a = x["start"] + (x["end"] - x["start"]) * acc / n_total
            acc += spoken_len(c)
            b = x["start"] + (x["end"] - x["start"]) * acc / n_total
            if not hidden and tidy(c):
                subs.append({"start": round(a, 3), "end": round(b + 0.25, 3), "text": tidy(c)})
    for cur, nxt in zip(subs, subs[1:]):  # 不让相邻两条字幕重叠
        cur["end"] = round(min(cur["end"], nxt["start"] - 0.04), 3)

    data = {"total": total, "sentences": timeline, "markers": markers, "subs": subs}
    (HERE / "timeline.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "timeline.js").write_text("window.TIMELINE = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    srt = "\n".join(f"{k}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['text']}\n" for k, s in enumerate(subs, 1))
    (HERE.parent / "subtitles.srt").write_text(srt, encoding="utf-8")
    print(f"{len(timeline)} 句，{len(markers)} 个关键词，{len(subs)} 条字幕，总长 {total:.1f} 秒")


if __name__ == "__main__":
    main()
