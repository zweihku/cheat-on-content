# works/ · 成片库

做好的视频放这里。一个系列一个文件夹，一集一个子文件夹；开始做一集就建它的文件夹，前期的稿子、美术、分镜也放在里面。

```
works/
├── README.md
├── .gitattributes             # 视频文件走 Git LFS
└── math-life/                 # 系列：数学 × 生活（哲理短片）
    ├── PLAN.md                # 选题规划
    └── EP01_他们都在哪儿/      # 一集一个文件夹
        ├── script.md          # 稿子
        ├── art-direction.md   # 美术方向
        ├── storyboard.md      # 分镜
        ├── frames/            # 美术样张（src/ 里是能重渲的源文件）
        ├── final.mp4          # 成片（做好后放）
        ├── cover.jpg          # 封面（可选）
        └── info.md            # 发布信息（发布后填）
```

## 命名

- 集文件夹：`EP<两位编号>_<短标题>/`。编号按发布顺序，短标题照抄 [math-life/PLAN.md](math-life/PLAN.md) 里的选题名
- 成片统一叫 `final.mp4`。不同平台出了不同版本，就叫 `final_douyin.mp4`、`final_bilibili.mp4`

## info.md 模板

```markdown
# EP01 他们都在哪儿

- 选题：B4（见 ../PLAN.md）
- 时长：3:20
- 发布：2026-10-xx · 抖音 <链接> · 视频号 <链接>
- 预测文件：predictions/2026-10-xx_f4b4ca22abbc_他们都在哪儿.md（走 cheat-on-content 流程时填）
- 复盘一句话：（T+3d 复盘后填）
```

## 大文件

- `.gitattributes` 已经把 mp4 / mov / m4v / webm / mkv 设成走 Git LFS。第一次往这里放视频前，在你电脑上跑一次 `git lfs install`（GitHub Desktop 自带 LFS）
- 不装 LFS 也能提交，但 GitHub 单个文件超过 50 MB 会警告，超过 100 MB 直接拒收
- LFS 的免费存储和流量有额度，视频多了可能要付费。不想占 repo 空间，就把成片放网盘，info.md 里只留链接

## 为什么不叫 videos/

本 repo 的 `.gitignore` 会在任意层级忽略 `videos/`、`scripts/`、`predictions/`、`candidates.md` 等（防止用户数据混进 skill 源码），所以成片库叫 `works/`。

如果之后在这个 repo 里跑 `/cheat-init`，它生成的稿子、预测、复盘也会被忽略，不会被提交。要留存的话，在跑 init 的那个目录里加一个 `.gitignore`，用 `!scripts/`、`!predictions/` 这类规则反向放行。
