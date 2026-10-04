# Brand Entity & Internal Knowledge Graph Audit

审计日期：2026-10-04。主站 P1 基线提交 `4a4603d`。没有搜索排名、Google 收录或外链增长的实测数据。本次审计覆盖主站生成器、公开研究 JSON、作者页、导航／页脚／内链／metadata／schema，以及独立 Global Pulse 的模板、云端适配、发布器和公开页面。

## 名称统计与计数范围

主站修改前统计 69 份 Git tracked 文本源文件（Python、JS、JSON、Markdown、HTML、CSS、YAML、PowerShell），排除生成 dist、vendor、字体／品牌／封面资产和运行目录。Global Pulse 修改前统计 34 份 tracked 自有文本文件，排除 vendor、品牌资产和测试。二进制 PDF／图片不做字符计数；历史稿件作者及关键词在 P1 已核对。

修改后扫描主站全部 110 份 canonical `index.html` 的可见文本与图片 alt（含 index/noindex，中英文各 55），排除 head、schema／script、404 和历史重定向。统计是名称出现次数，**不是搜索 impressions，也不是关键词密度目标**。英文名称区分大小写，RI / Sunny 用词边界；长名称与短名称可能重叠计数。

| 名称 | 主站源文件：修改前 | Global 源文件：修改前 | 主站可见 HTML：修改后 |
|---|---:|---:|---:|
| Residual Inertia | 61 | 20 | 514 |
| 余势 | 36 | 11 | 394 |
| Residual Inertia / 余势（字面斜杠写法） | 0 | 0 | 0 |
| RI | 49 | 15 | 60 |
| Taiyang Feng | 20 | 0 | 88 |
| Sunny | 33 | 8 | 12 |
| Sunny Feng | 2 | 0 | 0 |

源文件 Sunny 包括账号、测试 fixture 和六份历史报告的原始 author 字段，不全部属于公开署名。Sunny Feng 的两处是别名归一化规则及测试，修改后可见 HTML 没有该正式署名。RI 主要是公开报告 ID／品牌资产前缀，保留以免破坏核验及引用。高频品牌词主要来自既有 Logo、导航和页脚，不新增重复 SEO 文案。

Global 线上根页审计发现：已有 RI Logo，标题仍混用品牌／产品分隔写法；description 没有明确品牌关系，缺 canonical / JSON-LD；Logo href 为 `/`，公开全屏应用没有明确静态主站返回入口。本次在云端适配器补齐，原本地 dashboard 模板与地图业务保持。

## 统一规则

1. Organization 正式英文 name 为 Residual Inertia，alternateName 为余势。正文首次正式中文定义可写 Residual Inertia（余势）。
2. 现有 wordmark `Residual Inertia | 余势`、页脚双语分隔及设计中的英文大写保留：这是排版变体，不另建品牌实体。历史作者稿中的 Residual Inertia Investing 不批量改写成新版本。
3. 正式作者 Taiyang Feng；个人介绍 Taiyang Feng (Sunny)，中文语境括号可本地化。Sunny 不作为未来正式报告署名；Sunny / SunnyF419 的登录和仓库账号不改名。
4. 合著者姓名、顺序及历史稿件 attribution 保留。未知作者不自动归给创始人；组织发布使用既有 Organization。
5. Global Pulse / 全球态势是 RI 的研究观察系统，不是第二个 Organization。主站及子站共享 `https://residualinertia.com/#organization`。

## 实体及 HTML 内链

- 首页已有正式品牌定义、创始人／About 链接、Research 与 Market CTA，主导航能发现 Global Pulse；不重复增加大段文案。Hero slogan 保持原样。
- 修正英文 About title 重复品牌追加；Research metadata 说明真实作者、内容类型、数据日期与版本，不复制进正文。
- 两个代码库的 README 明确品牌与正式作者关系；主站 README 移除旧的未绑定域名、个人专题和 Sunny 正式署名说明。本地 Market Pulse 名称只说明开发版本，不另建品牌实体。
- WebSite 的 hasPart 指向核心页面；Research CollectionPage / ItemList 指向真实文章；AboutPage 的 about 指向 Organization 与 Person。
- Article / ScholarlyArticle 的 author 继续引用统一 Person，publisher 指向 Organization（外部学术论文只对本站 WebPage 声明 RI publisher）。
- About 保留品牌、原则、Founder 和两篇学术记录；补充简短真实研究流程及 Weekly、Policy、Thematic、Scholarly、Market、Global 六个可见入口。
- Research 首页保留最新 6 张卡片；可展开的研究方向说明提供分类、真实最新作品及作者链接。月报为 0 时明确待发布，不伪造“最新月报”。Scholarly 使用已有 `/research/personal/#scholarly-research`，不另建重复目录。
- Weekly / Monthly 根据 dataThrough 链接真实前期报告；只有正文确实提到 FOMC 才关联适用截止日的政策研究。学术论文以共享的真实关键词关联。没有手动改发布日期来排序前期报告。
- Snapshot 只关联 regimeDate 与报告 dataThrough 相同的市场报告；其余维持 Overview／前后档案导航，不机械匹配“最近上传”的文章。
- Overview 链到 About 中研究流程和 Global；Global 通过应用 WebPage / WebApplication 引用同一 Organization 与主站 WebSite，并在服务器 HTML 中提供主站返回链接。
- 没有隐藏链接、外链交换、重复文章副本或 footer 关键词堆积；研究方向 details 是用户可展开的正常内容。

## Topic inventory：按实质内容人工分类

共 8 份研究：5 周报、1 FOMC、2 SSRN 学术论文、0 月报。下面同一文章可属于多个主题；仅有词语提及不计入实质 cluster 数，快照和新闻条目不充当原创研究文章。

| 主题 | 实质文章数／依据 | 当前组织与判断 |
|---|---|---|
| Market Regime | 5；五期周报持续解释综合市场状态与风险维度 | Overview 与 Weekly archive 已可承载，不复制新 hub |
| Market Breadth | 5；五期周报讨论参与结构、宽度与指数背离 | 保留周报连续性及 Overview 链接 |
| Market Risk | 7；五期周报、FOMC 的权益风险影响、When Winners 的左尾风险 | 多种口径不能混成同一预测产品；已有 Market／Research 可组织 |
| Momentum | 2；两篇学术论文的核心方法问题 | 尚不足多篇长期主题 hub；互链两篇原研究 |
| Asset Pricing / Quantitative Investing | 2；两篇实证学术研究 | 作为研究方向，不批量生成 landing / tag pages |
| Macro / Policy | 3；FOMC、9 月 19 日周报政策落地、10 月 3 日周报 ACM 利率分解 | 已有 Policy archive；需更多独立政策研究后再评估专门主题页 |
| Semiconductor / AI Hardware | 5；五期周报的行业结构观察 | 属于周报子主题，尚无独立系列或长期计划的作者确认 |
| Global Markets events | 0 篇独立研究文章；已有 Global Pulse 事件系统 | 产品数据不计作研究发文数量，避免新闻 tag 泛滥 |

已有周报上传流程并不保证未来发文数量；本次没有替作者承诺长期 editorial calendar。Market Regime／Breadth 可优先深化现有 Overview＋Weekly 内容，任何新增 hub 需至少数篇独立实质研究、清晰的问题范围、作者审核和持续计划。

## 页面布局决策

复用 `/about/`、`/research/`、分类和 `/overview/`。不新增 `/methodology/`、`/data-sources/`、`/research-process/`：目前公开模型日期、来源质量、核验机制和论文方法分散在真实页面，没有经作者确认的独立完整方法论长文、统一数据许可表或独立研究流程文稿；复制这些说明会形成薄页面。方法说明整合到 About 的 `#research-process`，每篇论文和报告自己的方法／局限仍留在原文或 PDF。

## Freshness / editorial trust

所有已有 published / updated / version / dataThrough / researchId 保留。schema 只结构化已有版本、报告 ID 与截止日，不制造修订日期。文章仍显示作者、真实日期、来源／局限、PDF 方法和既有披露；没有为每篇增加长篇模板免责。新上传报告的日期标签明确 Published，公开作者归一化，不把登录名当作作者名；补齐原本遗漏的 note / dateLabel 字段以兼容生成器。

## 独立技术栈的共享方式

主站生成器从既有 `organization_node()` 输出 `/assets/brand/entity.json`。Global 的 `deployment/brand-entity.json` 是此导出的同步副本，`brand_metadata.py` 加载它，禁止再定义第二个机构 ID。更新品牌事实时先构建主站，再复制该导出到 Global；本地回归测试检查两者一致。Global bundle 必须包含 adapter 和 JSON。无运行时跨站 fetch、无 API token、无后台数据库导出。

Global 根页 self canonical 为 https://global.residualinertia.com/；主站 wrapper 仍 https://residualinertia.com/global/（英文对应 `/en/global/`）。两页分别是应用和站内介绍，不跨域合并。Global 只有一个服务器渲染的根页；query 切换语言是客户端 UI，不生成不存在的英文 hreflang。管理视图 noindex；认证、账户、发布和 API 不进入其 sitemap。主站的 P0/P1 sitemap 与真实翻译规则保留。

## 策略文档与未完成站外事项

- [External Authority Plan](EXTERNAL_AUTHORITY_PLAN.md)：三级执行计划、质量标准、人工 mention→link 模板及 30/60/90 天行动。
- [Author Identity Checklist](AUTHOR_IDENTITY_CHECKLIST.md)：正式姓名、作品归属、合著顺序和个人主页证据。
- [SEO Measurement Plan](SEO_MEASUREMENT_PLAN.md)：品牌 SERP 目标、真实 GSC 基线、query/referral/technical 监控。

SSRN external metadata、个人 academic profile、current affiliation、DOI 登记方更新、Search Console 验证与外部沟通均未代本人执行。不存在已实现的排名、sitelinks、backlink 或 academic endorsement 承诺。

## 本次代码验收与发布边界

- 主站生产构建成功：112 个正式 HTML（含两份 404），206 个含旧地址跳转的 HTML；公开链接／资产／隐私扫描通过。
- sitemap 102 个唯一生产 HTTPS URL；110 个 canonical index.html 均只有一份 JSON-LD graph、唯一实体 ID，noindex 页不在 sitemap。About 中英文 title 不重复品牌。
- 主站 26 个 Python tests、4 组 Node checks 通过；Global 66 个 Python tests、6 组 Node checks 和事件面板 mouse/touch/keyboard 浏览器测试通过。
- Global 生产包构建成功；其本地浏览器预览在 1440 / 390 宽度完成匿名读取、事件列表、详情和主站返回入口检查，无横向溢出或页面脚本错误。没有改登录安全、地图相机或拖动逻辑；旧测试调整为等待 resize 完成及合并小请求的网络写入，避免 Windows 时序误报。
- Python syntax / compile 与 diff whitespace 检查通过。项目没有独立 lint / TypeScript typecheck 配置，不能声称执行了不存在的命令。
- 本节记录提交与部署前的本地验收结果；当时尚未提交／推送或部署这批改动。后续发布状态以对应提交、部署记录及 Live SEO Verification 为准；本地通过不表示 Google 已抓取或选择本站声明的 canonical。
