# Residual Inertia | 余势

Residual Inertia（余势）是由 Taiyang Feng (Sunny) 创立的独立投资研究与决策系统平台，聚焦量化投资、资产定价、宏观市场、市场风险与研究基础设施。本仓库是品牌官网的静态发布代码，不代表所有研究的数据或复现代码。

正式网站：[Residual Inertia](https://residualinertia.com/)；[About / Founder](https://residualinertia.com/about/#founder)；[Research](https://residualinertia.com/research/)。

源码仓库：https://github.com/SunnyF419/residual-inertia-site 。GitHub 账号 `SunnyF419` 是账号标识，正式研究作者名为 Taiyang Feng。GitHub Actions 负责构建、公开内容检查与 Pages 部署；canonical 使用正式 HTTPS 域名。

## 本地查看

需要 Python 3.10 或更新版本，无第三方 Python / Node 构建依赖。

```powershell
python scripts/build.py
python scripts/check.py
python -m http.server 8788 --bind 127.0.0.1 --directory dist
```

浏览器打开 `http://127.0.0.1:8788`。首页与 Logo 链接使用站点根路径 `/`，请通过本地服务器预览。

## SEO 与语言对应

SEO 由现有 `scripts/build.py` 统一生成，不依赖额外 SEO 包。首页使用独立的中英文 title / description；品牌定义文本复用首页 description，Hero 标题仍由 `site.json` 控制。普通页面保留原有标题、说明和逐页 canonical。

Organization、Person 使用稳定的 `https://residualinertia.com/#organization`、`#taiyang-feng`；首页另外输出 `#website`。每页最多一个 JSON-LD graph，使用标准 `https://schema.org` context，以 Organization 的 `founder` 指向 Person。不要添加 Google 不接受的自定义 `founderOf` 反向属性；不把论文链接当作个人资料 `sameAs`。

完成双语构建后，只有两个实际生成、可索引且已提供对应翻译的页面才输出互相对应的 `zh-CN` / `en` / `x-default`。`x-default` 使用该页面的中文版本；首页为站点根路径。历史快照的评论及部分专题论文正文仍未完整翻译，因此暂不为这些详情页生成 hreflang。

`/research/monthly/` 与 `/en/research/monthly/` 按公开 `content/research/` 中的月报数量自动切换：0 篇为 `noindex, follow`，至少 1 篇为 `index, follow`。sitemap 仅收录可索引的正式页面，排除空月报目录、404 和旧地址跳转页，使用生产 HTTPS URL 并去重。robots.txt 保持允许抓取，指向唯一 sitemap。`tests/test_seo.py` 验证这些规则及首篇月报上线后的自动切换。

## 首页与导航

首页为 RI 品牌封面，展示正式 Logo、创始人 Taiyang Feng (Sunny) 和座右铭。原首页的指标、图表与近期记录移至 `/overview/`（市场概览）；所有页面使用目录式地址，例如 `/overview/`、`/about/`、`/research/`、`/snapshots/2026-09-29/`。旧 `.html` 地址保留即时跳转页，canonical 与 sitemap 指向新地址。

每日快照归入市场概览 `/overview/` 的 `#daily-snapshots` 区域，最近 5 份直接展示，其余记录可展开；旧快照目录自动跳转至该区域。研究按 `market`（周报与月报）、`personal`（专题研究，包含合著学术论文）、`fomc`（FOMC 政策研究）分目录。`personal` 是保留的路由标识，不表示所有内容由创始人独著。文章可用 `collection` 字段指定目录；未指定的周报/月报自动归入市场类，其他文章归入专题。尚未收录的目录明确显示待整理。

风险柱颜色按原模型状态映射：建设性为绿，谨慎/中性/防御为黄，压力为红；不修改分数或评级。

在 `site.json` 修改 `founder` 和 `motto`，即可同步更新首页、关于页及页脚。

## 内容与编辑

- `content/snapshots/*.json`：每日市场归档的公开字段；日期与数量以实际文件及构建输出为准。
- `content/research/*.json`：研究文章，`markdown` 字段支持标题、粗体、段落、无序列表、引用和表格；不解释原始 HTML。
- `assets/site.css`：RI 品牌页面样式。Logo、字体来自现有门户，字体授权保留在 `assets/brand/fonts/`。
- `scripts/build.py`：生成完整 HTML；无客户端 API、数据库、账户登录或实时行情依赖。
- `dist/`：生成结果，Git 忽略；GitHub Actions 每次从已提交内容重建。

公开报告以 `content/research/` 的正式记录为准，保留源报告数据、署名、日期、版本与方法说明，排除本机运行日志。报告发布日期和数据截止日不等同于网站上线日期。

## 每日更新

原研究门户与定时归档继续独立运行。本仓库只读既有 JSON，不触发研究计算，不改写数据库。

```powershell
.\Update Website.ps1 -PortalPath 'E:\QuantResearchHub\recurring_workflows\quant_research_portal'
```

检查后，加 `-Publish` 可将新增公开内容提交并推送，触发 Pages 更新；需要本机已登录 GitHub。`PortalPath` 默认使用同级 `quant_research_portal`。

已接入原有 Windows 任务 `Residual Inertia Investing - Daily Portal Archive`：周一至周六 10:00 更新数据，成功建档后运行网站发布。当天已存在快照时，仅补做网站同步。同步失败会让任务失败并沿用每 15 分钟、最多 3 次的重试设置；失败不删除快照，不替换线上部署。构建或校验失败时不推送，GitHub Pages 构建失败时保留之前的线上版本。

任务以 THINKBOOK 登录会话运行，电脑需开机、该用户已登录并能联网；错过时间使用原任务的补跑设置。周日不创建快照。新研究正文仍需作者单独上传发布。

另有独立任务 `Residual Inertia - Website Data Sync`，登录后监听 dashboard 更新完成的事件，不定时发布。运行 `Install Website Sync Task.ps1` 安装，`Run Website Sync.ps1` 手动执行，`-CheckOnly` 只验证不推送。统一门户更新记录必须为 `success`、事务 `committed` 且质量 `pass/warning`；更新运行锁释放后才发布。dashboard 自身更新按钮在成功退出且信号文件改变后写入完成标识，同样经过公开字段、质量与历史一致性校验。失败、回滚、未完成的更新不会触发推送；网络失败只重试已有成功事件，登录后也会补发尚未完成的事件。

发布只刷新门户摘要、读取既有 dashboard 输出，不启动研究计算，也不创建或改写每日正式归档。完整门户归档被其他来源的更新错误阻断时，已通过市场质量检查的数据仍可发布。事件监听器不需要重启门户服务。

`content/market/latest.json` 保存最新有效市场观察，供市场概览和 `/market/latest/` 使用。每项指标仍显示自己的截止日期，同步时间单独标明；它不是当天的正式归档。`content/snapshots` 继续保存不可变的每日历史记录。市场来源不可用、质量失败、数值非法或数据日期倒退时保留上一有效观察；最新分数与数据库历史终点不一致时阻止发布。其他来源的持仓、任务日志和报告不进入最新市场观察。

独立同步日志和结果位于网站 `.runtime/website-sync/sync.log`、`latest.json`，完成事件见 `events.log` 和 `completed.json`。没有内容变化时不会提交或触发重新部署。公开 JSON 先推送到 GitHub 仓库，随后由 Pages 构建部署。Python、Node 与 Git 的路径在安装时保存，供后台会话使用；Git 使用带证书校验的 OpenSSL 后端。后台任务仍要求电脑开机、THINKBOOK 登录、网络和 GitHub 凭据可用。

运行日志在门户的 `.runtime/daily-archive/logs/windows-task.log`；网站成功推送不等于 Pages 已完成上线，部署结果见 GitHub Actions。入口脚本的备份位于 `automation/Run Daily Portal Archive.ps1`，实际任务执行的是门户目录中的同名文件。网站有未提交代码或已有暂存修改时，自动发布停止，避免混入正在编辑的内容。

导出采用字段白名单：市场风险、状态、宽度、风险支柱、数据日期、公开风险提示、来源质量状态、快照核验标识。不导出实际账户、个股持仓清单、FOMC 未复核原文、数据库路径、任务日志、localhost 地址或密钥。

已有观察日若源内容被修订，导入会停止而不是自动覆盖历史；需检查差异后显式修订对应公开内容。研究报告默认仅首次导入，可在公开副本中编辑，不会被后续导入覆盖。

**静态托管不会运行本机研究程序。** GitHub 只发布已经推送的公开内容；本机未运行或未推送时，网站停留在上一归档日，并显示真实日期。

## 部署

见 [DEPLOY.md](DEPLOY.md)。GitHub Pages 已绑定 `https://residualinertia.com/`，自定义域名与 HTTPS 已启用。

## SSRN 论文页面

论文仍使用 `content/research/*.json`，归入 `personal`。`summary` 为简介；`published` 搭配 `dateLabel` 标明日期含义，`updated` 为可选修订日期；`author`、`subtitle` 展示作者与副标题。`pdf` 指向 `assets/papers/` 下的真实 PDF，`pdfSha256` 保存文件校验值；`ssrnUrl` 链接到原文。`note` 明确网站下载版本，`sourceNote` 记录来源与研究局限。替换 PDF 时同步更新版本说明与校验值。

## P1 作者、研究与历史快照 SEO

P2 品牌审计与长期执行文档位于 `docs/seo/`：[品牌实体审计](docs/seo/BRAND_ENTITY_AUDIT.md)、[站外权威计划](docs/seo/EXTERNAL_AUTHORITY_PLAN.md)、[作者身份清单](docs/seo/AUTHOR_IDENTITY_CHECKLIST.md)、[监控计划](docs/seo/SEO_MEASUREMENT_PLAN.md)。这些文档不是站外账号修改或排名增长的完成证明。Global Pulse 与主站共用 Organization ID；主站生成 `/assets/brand/entity.json`，子站同步此公开导出，不复制私有数据。

继续使用 `scripts/build.py` 的统一 JSON-LD graph，不添加客户端 SEO 包。每个文档只输出一次 Organization 与 Taiyang Feng Person 定义，文章通过 `@id` 引用。作者页复用 `/about/#founder`；Sunny、Sunny Feng 与 Taiyang Feng 是已确认的同一作者别名，公开署名统一为 Taiyang Feng。合著者保持原署名及顺序，未知作者不自动归到创始人；组织或缺省发布署名使用 Organization。Person 没有可靠的个人主页、ORCID 或 SSRN author profile，因此不添加 `sameAs`；论文 landing page 只属于论文实体。

普通周报、月报、专题和政策研究输出 Article。有记录的 SSRN / DOI 学术论文输出 ScholarlyArticle：保留作者顺序、实际发布日期与可选修订日期，关联站内 self canonical 和外部 landing page。SSRN PDF 不能作为 landing page，DOI 必须存在于 `doi` / `doiUrl` 字段，不从 SSRN 编号推导。现有两篇论文的 `keywords` 和 `manuscriptStatus` 来自本地作者稿；状态只描述本站版本，不代表 SSRN 最新版本、同行评审或期刊录用。RI 作为论文站内 WebPage 的 publisher，不声称是外部学术论文的原出版机构。

研究目录、分类目录、文章和快照均在同一 graph 内输出 BreadcrumbList，沿用既有页面返回导航。快照归档仍位于 `/overview/#daily-snapshots`，原 `/snapshots/` 重定向保持不变。研究页输出对应 OG / Twitter title、description、URL 和 article 类型，不生成新的社交图片。

`snapshot_index_decision(snapshot, earlier)` / `should_index_snapshot` 是 HTML robots 与 sitemap 共用的索引决策入口：必须具备有效日期、核验标识、公开市场来源质量、风险级别、综合分数、仓位、宽度、四个风险维度和文字判断。新数据日期组合（signal / effective / regime / breadth）可索引；相同日期组合只有风险状态或评论／告警文字变化才可索引。比较文字时忽略重新填入模板的数字，不按任意分数涨跌阈值判定。索引失败不删除档案、不改导航、不合并 canonical；所有快照继续 self-reference。

人工治理放在 `content/snapshot-indexing.json`，不污染不可变的快照内容或哈希。例如（示例不默认生效）：

```json
{"version": 1, "overrides": {"2026-09-08": {"index": false, "reason": "与前一日同一数据版本，无新增文字判断"}}}
```

每条覆盖必须使用布尔 `index` 并提供非空 `reason`；显式 `true` 可以保留有编辑价值的同版本档案，但不能绕过数据完整性检查。noindex 页面仍输出 Dataset、Breadcrumb 和正确 canonical，同时从 sitemap 排除。归档及索引快照公开 Dataset 与来源日期、快照标识、SHA-256 和八项市场测量字段，不披露后台数据库或账户资料。

构建验收：`python scripts/build.py`、`python scripts/check.py`、`python -m unittest discover -s tests -p 'test_*.py'`，以及现有四个 Node 验证脚本。项目没有单独的 lint / TypeScript typecheck 命令；新增 P1 测试覆盖实际中英文 HTML、合著者与实体引用、论文关联、面包屑、社交元数据、索引政策及 sitemap。

## 七段首页

首页依次展示 Hero、市场状态、最新研究、研究方向、Systems、Founder、品牌理念。市场摘要与完整概览共用最新归档，最新研究按报告日期排列。系统与创始人导航指向首页对应区块，Dashboard 指向市场概览；文章及快照保持简洁地址。

## 五年市场状态历史

市场概览图读取 `content/market/regime-history.json`。同步时，导入器从门户配置定位市场研究项目，再读取该项目 `config.yaml` 的 `paths.duckdb_path`，以支持迁移至统一数据库目录；旧项目没有配置时才使用 `data/dashboard.duckdb`。只读 `market_regime_history` 的日期、综合分数和中文状态。以最新有效观察的 `regimeDate` 为窗口终点，保留前五个日历年的数据，不补齐缺失日期。该历史序列沿用当前模型口径，源数据修订可能影响历史分数，不替代不可变的每日快照。

本地导入需要现有 Python 环境中的 `duckdb`；GitHub 构建只读取已导出的 JSON，仍无数据库依赖。历史源不可读取、覆盖不足或数值非法时，同步失败并阻止推送，保留线上版本。

正式市场周报和月报由作者登录后上传 PDF 发布，不再由 dashboard 导入。网站读者可注册账户，但没有上传或修改权限。作者登录使用 Microsoft Authenticator 二次认证，首次登录先绑定验证器；密码正确而二次认证未通过不会获得管理权限。报告先上传成私有草稿，预览无误后单独发布。文章展示简介、日期与浏览 PDF 入口。

每日 Update Website.ps1 -Publish 会先拉取并合并作者从网站上传的报告；并发发布时重新同步、构建并验证后重试，防止日常快照更新覆盖正式报告。自动发布连接需要服务器专用的仓库写入密钥，当前等待用户明确授权，上传与草稿预览不受影响。
