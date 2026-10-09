# EP01 动态版（animatic）

按 [storyboard.md](../storyboard.md) 渲染的竖屏动态画面，1080×1920，30 帧，约 3 分 24 秒。**这不是成片**：还没有你的旁白，时间是按稿子估的语速排的。

| 文件 | 是什么 | 用途 |
|---|---|---|
| `EP01_preview.mp4` | 带字幕 + 临时配乐 | 先看整体节奏和画面 |
| `EP01_clean.mp4` | 无字幕、无声音 | 进剪映剪辑用 |
| `subtitles.srt` | 字幕文件，55 条 | 剪映里"导入字幕"，或者对着念 |

临时配乐是用代码合成的（低频铺底、三声磬、连乘时的轻响、无线电底噪、唱片沙沙声），没有用任何采样素材，只用来感受节奏，正式版换成真的配乐。

## 时间是怎么排的

- 旁白按每分钟约 216 字估算，每句后留 0.6 秒气口，最后停 4 秒
- 画面上的动作都挂在稿子里的关键词上：念到「乘上有行星的」那一项才刻出来，念到「最后剩下 26 个」星尘才熄到只剩 26 颗，念到「谁先认真」城里才灭一扇窗
- 开场那句、金唱片的问候、结尾 outro 画面上有竖排大字，这几处不出字幕；「十二年，少了一半」也一样

## 录完旁白之后：让画面贴着你的录音

你念的速度不会和估算的一样。有两种办法：

1. **剪映里调**（快）：把 `EP01_clean.mp4` 按分镜的时间码切开，每段用变速或定格拉长、缩短，对上你的录音。画面都很慢，±20% 的变速看不出来
2. **重渲**（准）：把录音发给我，或者自己记下每句话的开始时间（秒），一行一个写进 `src/sentence_starts.txt`（32 行，和稿子的句子一一对应），然后：

```bash
cd src
python3 timing.py      # 按你的时间重算关键词和字幕
python3 sound.py       # 重新合成临时配乐（可选）
node render.cjs        # 重渲两个视频
```

渲染需要 Node 和 Playwright（`npm i playwright && npx playwright install chromium`），整片大约 15–20 分钟。只想看某几个时间点，用 `node render.cjs --stills 12,36,68`。

## 源文件

| 文件 | 作用 |
|---|---|
| `src/animatic.html` | 动画本身（HTML + Canvas + SVG），`seek(t)` 画出第 t 秒的画面 |
| `src/timing.py` | 从 `script.md` 算时间轴，生成 `timeline.js` / `timeline.json` / `subtitles.srt` |
| `src/sound.py` | 合成临时配乐 `temp_audio.wav`（这个 wav 不进 git，随时能重新生成） |
| `src/render.cjs` | 逐帧截图，用 ffmpeg 编码成 mp4 |

改了稿子（`script.md`）以后，先跑 `timing.py`。如果改动删掉了动画挂靠的关键词，脚本会直接报出是哪个词，到 `timing.py` 开头的 `MARKERS` 里改掉就行。
