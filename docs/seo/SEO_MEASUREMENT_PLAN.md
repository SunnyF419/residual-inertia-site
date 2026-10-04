# Residual Inertia — SEO Measurement Plan

日期：2026-10-04。尚无 Search Console、analytics、排名或站外 referral 的授权数据；基线统一标为 **待采集**，不能写 0 或推测增长。代码通过和部署成功不等于 Google 已重新抓取、索引或提升排名。

## 权限与基线

由 Taiyang Feng 验证 Search Console 的 `residualinertia.com` Domain property，覆盖主站及 global 子域；需要域名 DNS 权限。没有 Domain property 权限时，分别验证两个 HTTPS URL-prefix property，并分开记录。提交 https://residualinertia.com/sitemap.xml 与 https://global.residualinertia.com/sitemap.xml。不在仓库放验证 token 或账号凭据。

首次保留日期、property、查询过滤器、语言／国家／设备、可用区间和导出文件。用最近完整 28 天与前 28 天比较，每月另看三个月趋势；新站数据不足时使用实际可用天数，不补零。发布版本与内容变更单独记录，避免把新文章、季节性或样本差异误当成 SEO 改动效果。

## Brand Search

| 查询分组 | 过滤器与目的 | 指标 | 频率 |
|---|---|---|---|
| 正式英文品牌 | `(?i)residual\s+inertia`；另核对 investment research 扩展 | impressions、clicks、CTR、显示的页面 | 每周 |
| 作者＋品牌 | `(?i)(residual\s+inertia.*taiyang\s+feng|taiyang\s+feng.*residual\s+inertia)` | 关系查询的曝光与落地页 | 每周 |
| 正式作者 | `(?i)taiyang\s+feng` | 作者页／论文页曝光；逐条排除同名人的无关意图 | 每月 |
| 中文品牌 | `余势`；另外查看 `余势.*投资研究` | 中文品牌曝光与页面匹配 | 每周 |
| 正式论文标题 | 分别匹配 Winners Glide, Losers Stumble / When Winners Stop Winning | 论文页曝光、CTR、自然入口 | 每月 |

分别保存五个目标搜索词：Residual Inertia；Residual Inertia investment research；Residual Inertia Taiyang Feng；Taiyang Feng Residual Inertia；余势 投资研究。RI 和 Sunny 太宽泛，不计入主要品牌指标。

GSC 若显示官方 Branded / Non-branded filter 可以辅助使用；低曝光站点可能没有该选项，继续用明确 regex 和人工抽样，不假装有数据。Regex 使用 RE2；过滤后的查询包含隐私／匿名查询限制，不能把品牌曝光份额当成精确全量占比。依据：[Performance use cases](https://support.google.com/webmasters/answer/17010961?hl=en)、[Advanced filtering](https://support.google.com/webmasters/answer/17011165?hl=en)、[Query data limitations](https://support.google.com/webmasters/answer/10268906?hl=en)。

## Search Console 与 Sitelinks readiness

| 指标 | 检查与解释 | 处理方式 |
|---|---|---|
| Branded impressions / CTR | 同一过滤器、property、区间和设备比较，观察品牌落地页是否合理 | 低样本不作排名结论；核对 title 与实际查询意图 |
| Indexed / excluded pages | 对照当前 sitemap 和索引政策，而不是追求所有 URL index | 空月报和治理后的重复快照 noindex 属预期；调查意外 excluded |
| Crawl issues | URL Inspection 抽查首页、About、Research、论文和各一个 index/noindex 快照 | 核对抓取日期、HTTP 状态、robots、canonical；不要批量 Request Indexing |
| Sitelink-like query patterns | 品牌查询实际显示哪些站内页面；手工记录核心链接与截图日期／地区 | GSC 没有可保证的 sitelinks 成功指标；页面列表不是 sitelinks 出现的证明 |
| Research queries | 分别看 market regime、risk、momentum、paper title 相关真实查询 | 根据读者问题改进原创研究，不复制查询生成批量页面 |

Google 自动决定 sitelinks，逻辑导航、描述明确的 title 和相关内链只是结构准备，不能强制显示。依据：[Google sitelinks](https://developers.google.com/search/docs/appearance/sitelinks)。

## Research 与 Referral

- 论文标题／作者查询：GSC 按具体站内论文 URL 和 query 查看，保留论文版本与发布时间。
- Research page organic entrances：需要本人批准并实际启用的 analytics 或可用的站点日志；GSC clicks 不能直接称作 analytics sessions。
- SSRN referral：只有有 inbound referrer 的 analytics／日志才能测量。站内点击 SSRN 是 outbound，不是 SSRN referral；`noreferrer`、浏览器限制和直接访问会造成缺失。当前主站没有配置该测量，不虚构访问量。
- GitHub Pages 主站不能假设提供可导出的服务器 access log；Global Pulse 日志只反映子站。若以后启用 analytics，只收集必要的聚合流量，避免把账户或新闻管理数据发送给第三方。
- 每月复核高质量独立研究引用，记录准确作品、作者归属和实际来源链接，不以 backlink 总数作为目标。

## Technical

| 项目 | 基线／检查 | 频率与责任 |
|---|---|---|
| Sitemap | 主站本次预期 102 个唯一生产 URL；Global Pulse 只有公开根页。以未来构建输出为准 | 每次发布自动验收；每周 GSC 状态，维护者 |
| Canonical | 抽查 self canonical；主站 Global wrapper 与 Global application 各自 self-reference，不跨域合并 | 每次发布；GSC 检查 Google-selected canonical |
| Structured data | 单 graph、唯一实体 ID；文章／合著者／publisher／Breadcrumb／Dataset 引用真实 | 本地测试＋Schema Validator；支持的 Google feature 再用 Rich Results Test |
| Hreflang | 只有真实翻译且可索引的页互相对应；无英文正文的档案不冒充翻译；Global query-language UI 不建假 hreflang | 每次发布，保留 P0/P1 回归测试 |
| Core Web Vitals | 每月固定手机／桌面检查首页、Research、论文、About、Overview 与 Global 地图。记录工具、网络、样本与日期 | 用真实 field data；若无 CrUX/GSC 样本，标“无足够数据”，lab results 单列 |
| Broken links / privacy | 现有生成器检查、站内锚点、公开资料扫描、认证与地图测试 | 每次发布，不导出后台资料 |

官方字段标准：[Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals)。P2 没有安装 analytics、扩大追踪或进行账户授权。

## 品牌 SERP 目标矩阵

这是希望自然出现的页面组合，不是排序承诺：

| 结果角色 | 目标 URL | 页面准备 |
|---|---|---|
| 品牌首页 | https://residualinertia.com/ | P0 正式品牌 title、定义文本、创始人链接、WebSite / Organization / Person |
| Research | https://residualinertia.com/research/ | 分类说明、最新研究、作者链接、CollectionPage / ItemList |
| Market Overview | https://residualinertia.com/overview/ | 数据日期、模型状态、快照、方法与 Global 内链 |
| About | https://residualinertia.com/about/ | 品牌、创始人、原则、研究流程、作品及系统 |
| Global Pulse | https://residualinertia.com/global/ 与 https://global.residualinertia.com/ | 站内介绍与实际应用分工；同 Organization、各自 canonical |
| Academic result | 已有两个 SSRN landing page | 本人核对外部 metadata 和网站字段；未确认其当前 SERP 表现 |
| Key papers | https://residualinertia.com/research/winners-glide-losers-stumble/ 等 | 标题、合著者、摘要、版本与学术标识 |

## 每月复盘记录

| 周期／property | 品牌曝光与 CTR | 作者／论文 query | 索引与排除原因 | crawl / canonical / schema / hreflang | CWV 样本 | 已验证独立引用 | 下一项研究质量改进 |
|---|---|---|---|---|---|---|---|
| 首次基线 | 待本人授权采集 | 待采集 | 待 GSC 核对 | 本地验收通过不代表 Google 状态 | 待采集 | 待核实 | 根据实际读者问题决定 |

如果主站首页被意外 noindex、核心页返回错误、sitemap 出现外部／开发 URL、canonical 跨域错误或 schema 产生重复实体，按技术事故及时处理。正常索引延迟、低曝光或暂未显示 sitelinks不等同于故障。
