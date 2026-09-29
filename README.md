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

浏览器打开 `http://127.0.0.1:8788`。亦可直接打开 `dist/index.html`，正常页面的导航和本地资源使用相对路径。

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

检查后，加 `-Publish` 可将新增公开内容提交并推送，触发 Pages 更新；需要本机已登录 GitHub，且首次部署已完成。它不自动创建 Windows 计划任务。当前也没有把该命令接入原有日更任务。

导出采用字段白名单：市场风险、状态、宽度、风险支柱、数据日期、公开风险提示、来源质量状态、快照核验标识。不导出实际账户、个股持仓清单、FOMC 未复核原文、数据库路径、任务日志、localhost 地址或密钥。

已有观察日若源内容被修订，导入会停止而不是自动覆盖历史；需检查差异后显式修订对应公开内容。研究报告默认仅首次导入，可在公开副本中编辑，不会被后续导入覆盖。

**静态托管不会运行本机研究程序。** GitHub 只发布已经推送的公开内容；本机未运行或未推送时，网站停留在上一归档日，并显示真实日期。

## 部署

见 [DEPLOY.md](DEPLOY.md)。GitHub 仓库和 Pages 已启用；剩余 Cloudflare DNS、自定义域名与该域名的 HTTPS 验证。
