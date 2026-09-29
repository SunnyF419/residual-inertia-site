# GitHub Pages + Cloudflare 域名

目标域名：`residualinertia.com`。GitHub：`SunnyF419`。仓库名：`residual-inertia-site`。

## 当前状态

- 仓库已创建并推送；Pages 已启用。
- 首次成功部署：https://github.com/SunnyF419/residual-inertia-site/actions/runs/36506747793
- 当前网站：https://sunnyf419.github.io/residual-inertia-site/
- 线上桌面和手机页面、字体图片、导航、研究表格检查通过。
- 根域名与 www 尚无有效网站解析；Cloudflare 操作等待账号/浏览器连接。
- 以下第 1–2 步为重新部署参考，当前无需重复创建仓库。

## 1. GitHub 仓库

在 https://github.com/new 创建名为 `residual-inertia-site` 的空仓库，不添加初始 README。使用 GitHub Free 时，GitHub Pages 需要公开仓库；如需私有源码，先确认账号套餐支持私有仓库 Pages。发布的网站本身是公开的。

本地网站只包含整理后的公开内容，不要上传原始研究门户或整个 QuantResearchHub。

登录 GitHub 后，在本项目目录执行：

```powershell
git remote -v
git push -u origin main
```

本地 `origin` 已按计划配置为 `https://github.com/SunnyF419/residual-inertia-site.git`。如改用其他仓库，请调整 remote。

## 2. 启用 Pages

仓库 Settings → Pages → Build and deployment → Source 选择 **GitHub Actions**。
在 Actions 中手动运行 **Publish Residual Inertia**（首次 push 可能早于启用 Pages，必要时重新运行）。等待部署成功后验证 GitHub 提供的网站地址。

## 3. 绑定域名

先在 GitHub 账号 Settings → Pages 验证 `residualinertia.com` 所有权，按 GitHub 实际给出的 TXT 名称和值在 Cloudflare 添加记录。

然后在仓库 Settings → Pages 的 **Custom domain** 设置 `residualinertia.com`。
本项目采用 Actions 发布：输出中的 CNAME 仅作为站点域名声明；**它不能替代仓库 Pages 的 Custom domain 设置**。

在 Cloudflare 对应域名的 DNS 页面配置以下记录（先检查现有记录，避免覆盖邮件或其他业务）：

| 类型 | 名称 | 内容 | 代理 |
| --- | --- | --- | --- |
| A | @ | 185.199.108.153 | DNS only |
| A | @ | 185.199.109.153 | DNS only |
| A | @ | 185.199.110.153 | DNS only |
| A | @ | 185.199.111.153 | DNS only |
| CNAME | www | SunnyF419.github.io | DNS only |

TTL 可用 Auto。`www` 的 CNAME 不应包含仓库名或 URL 路径。初次接入用灰云 DNS only，方便 GitHub 校验域名和签发 HTTPS 证书。不要保留同名冲突记录或指向旧主机的 AAAA 记录；仅调整本网站相关条目，保留 MX/TXT 等其他服务记录。

等待 GitHub 域名检查通过和证书就绪，再勾选 **Enforce HTTPS**。验证根域名、www 重定向、任意快照详情页和研究页。此步骤需要域名管理权限，当前未代为修改 DNS。

## 4. 后续发布

推送 `main` 触发：构建 → 页面链接/资源/公开内容检查 → 仅上传 `dist` → Pages 部署。
研究运算继续留在本机；工作流不访问本机 E 盘，也不自动抓取最新市场数据。

## 官方参考（2026-09-29 核对）

- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
- https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages
- https://developers.cloudflare.com/dns/manage-dns-records/reference/dns-record-types/
