# Residual Inertia | 余势

面向 `residualinertia.com` 的纯静态研究网站。GitHub 账号：`SunnyF419`；仓库：`residual-inertia-site`。

网站已发布：https://sunnyf419.github.io/residual-inertia-site/
源码仓库：https://github.com/SunnyF419/residual-inertia-site

GitHub Actions 已通过构建、公开内容检查与 Pages 部署，线上桌面/手机页面及导航检查通过。自定义域名暂未绑定，等待 Cloudflare DNS 接入。

## 本地查看

需要 Python 3.10 或更新版本，无第三方 Python / Node 构建依赖。

```powershell
python scripts/build.py
python scripts/check.py
python -m http.server 8788 --bind 127.0.0.1 --directory dist
```

浏览器打开 `http://127.0.0.1:8788`。首页与 Logo 链接使用站点根路径 `/`，请通过本地服务器预览。

## 首页与导航

首页为 RI 品牌封面，展示正式 Logo、创始人 Sunny 和座右铭。原首页的指标、图表与近期记录移至 `/overview/`（市场概览）；所有页面使用目录式地址，例如 `/overview/`、`/about/`、`/research/`、`/snapshots/2026-09-29/`。旧 `.html` 地址保留即时跳转页，canonical 与 sitemap 指向新地址。

每日快照归入市场概览 `/overview/` 的 `#daily-snapshots` 区域，最近 5 份直接展示，其余记录可展开；旧快照目录自动跳转至该区域。研究按 `market`（周报与月报）、`personal`（个人专题，如 WQS）、`fomc`（FOMC 政策研究）分目录。文章可用 `collection` 字段指定目录；未指定的周报/月报自动归入市场类，其他文章归入个人专题。尚未收录的目录明确显示待整理。

风险柱颜色按原模型状态映射：建设性为绿，谨慎/中性/防御为黄，压力为红；不修改分数或评级。

在 `site.json` 修改 `founder` 和 `motto`，即可同步更新首页、关于页及页脚。

## 内容与编辑

- `content/snapshots/*.json`：每日市场归档的公开字段；已接入 2026-08-24 至 2026-09-28 的 31 份档案。
- `content/research/*.json`：研究文章，`markdown` 字段支持标题、粗体、段落、无序列表、引用和表格；不解释原始 HTML。
- `assets/site.css`：RI 品牌页面样式。Logo、字体来自现有门户，字体授权保留在 `assets/brand/fonts/`。
- `scripts/build.py`：生成完整 HTML；无客户端 API、数据库、账户登录或实时行情依赖。
- `dist/`：生成结果，Git 忽略；GitHub Actions 每次从已提交内容重建。

初始研究文章来自 2026-08-12 周报和 2026-08-15 月报。保留源报告数据与方法说明，移除本机运行日志；不是新完成的研究或当前市场建议。网站上的原报告生成日不代表网站已经于当时上线。

## 每日更新

原研究门户与定时归档继续独立运行。本仓库只读既有 JSON，不触发研究计算，不改写数据库。

```powershell
.\Update Website.ps1 -PortalPath 'E:\QuantResearchHub\recurring_workflows\quant_research_portal'
```

检查后，加 `-Publish` 可将新增公开内容提交并推送，触发 Pages 更新；需要本机已登录 GitHub。`PortalPath` 默认使用同级 `quant_research_portal`。

已接入原有 Windows 任务 `Residual Inertia Investing - Daily Portal Archive`：周一至周六 10:00 更新数据，成功建档后运行网站发布。当天已存在快照时，仅补做网站同步。同步失败会让任务失败并沿用每 15 分钟、最多 3 次的重试设置；失败不删除快照，不替换线上部署。构建或校验失败时不推送，GitHub Pages 构建失败时保留之前的线上版本。

任务以 THINKBOOK 登录会话运行，电脑需开机、该用户已登录并能联网；错过时间使用原任务的补跑设置。周日不创建快照。门户内手动更新不会立即推送，需等待任务或运行 `Update Website.ps1 -Publish`。新研究正文仍需单独整理发布，此流程自动同步的是每日市场快照。

运行日志在门户的 `.runtime/daily-archive/logs/windows-task.log`；网站成功推送不等于 Pages 已完成上线，部署结果见 GitHub Actions。入口脚本的备份位于 `automation/Run Daily Portal Archive.ps1`，实际任务执行的是门户目录中的同名文件。网站有未提交代码或已有暂存修改时，自动发布停止，避免混入正在编辑的内容。

导出采用字段白名单：市场风险、状态、宽度、风险支柱、数据日期、公开风险提示、来源质量状态、快照核验标识。不导出实际账户、个股持仓清单、FOMC 未复核原文、数据库路径、任务日志、localhost 地址或密钥。

已有观察日若源内容被修订，导入会停止而不是自动覆盖历史；需检查差异后显式修订对应公开内容。研究报告默认仅首次导入，可在公开副本中编辑，不会被后续导入覆盖。

**静态托管不会运行本机研究程序。** GitHub 只发布已经推送的公开内容；本机未运行或未推送时，网站停留在上一归档日，并显示真实日期。

## 部署

见 [DEPLOY.md](DEPLOY.md)。GitHub Pages 已绑定 `https://residualinertia.com/`，自定义域名与 HTTPS 已启用。

## SSRN 论文页面

论文仍使用 `content/research/*.json`，归入 `personal`。`summary` 为简介；`published` 搭配 `dateLabel` 标明日期含义，`updated` 为可选修订日期；`author`、`subtitle` 展示作者与副标题。`pdf` 指向 `assets/papers/` 下的真实 PDF，`pdfSha256` 保存文件校验值；`ssrnUrl` 链接到原文。`note` 明确网站下载版本，`sourceNote` 记录来源与研究局限。替换 PDF 时同步更新版本说明与校验值。

## 七段首页

首页依次展示 Hero、市场状态、最新研究、研究方向、Systems、Founder、品牌理念。市场摘要与完整概览共用最新归档，最新研究按报告日期排列。系统与创始人导航指向首页对应区块，Dashboard 指向市场概览；文章及快照保持简洁地址。

## 五年市场状态历史

市场概览图读取 `content/market/regime-history.json`。每日同步时，导入器从门户配置中的市场研究项目定位 `data/dashboard.duckdb`，只读 `market_regime_history` 的日期、综合分数和中文状态。以最新归档的 `regimeDate` 为窗口终点，保留前五个日历年的数据，不补齐缺失日期。该历史序列沿用当前模型口径，源数据修订可能影响历史分数，不替代不可变的每日快照。

本地导入需要现有 Python 环境中的 `duckdb`；GitHub 构建只读取已导出的 JSON，仍无数据库依赖。历史源不可读取、覆盖不足或数值非法时，同步失败并阻止推送，保留线上版本。

正式市场周报和月报由作者登录后上传 PDF 发布，不再由 dashboard 导入。网站读者可注册账户，但没有上传或修改权限。作者登录使用 Microsoft Authenticator 二次认证，首次登录先绑定验证器；密码正确而二次认证未通过不会获得管理权限。报告先上传成私有草稿，预览无误后单独发布。文章展示简介、日期与 PDF 下载。

每日 Update Website.ps1 -Publish 会先拉取并合并作者从网站上传的报告；并发发布时重新同步、构建并验证后重试，防止日常快照更新覆盖正式报告。自动发布连接需要服务器专用的仓库写入密钥，当前等待用户明确授权，上传与草稿预览不受影响。
