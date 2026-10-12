# 主域名账户服务迁移

## 状态（2026-10-12）

账户中英文界面、表单、跳转、报告管理，以及 Cloudflare 账户路由代码已准备。
账户后端与 Cloudflare 主域名网关已部署，主站配置已切换为主域名。
线上中英文登录/注册、未登录账户与报告管理跳转、语言 cookie、账户资源、
会话接口、错误密码及跨站 Origin 拒绝检查通过。
作者真实登录与 MFA、邮箱绑定、上传和发布仍需本人使用现有账户验收；
未创建生产测试账户、未读取 MFA 密钥、未发布测试报告。

Worker 版本：`e816b439-5a68-4d40-ab11-531ca25e3fda`。
后端代码和环境备份：`/root/ri-account-backup-20261012T020142Z`。
上游请求使用 `cache: 'no-store'`，避免缓存覆盖移除 Set-Cookie；
测试确认语言与登录两条 cookie 分别保留，线上语言 cookie 已验证。

## 用户看到的入口

| 功能 | 最终主站路径 |
| --- | --- |
| 登录 | `/auth/login?next=%2Faccount&lang=en` 或 `lang=zh` |
| 注册 | `/auth/register?lang=en` 或 `lang=zh` |
| MyRI / 账户 | `/account?lang=en` 或 `lang=zh` |
| 作者报告管理 | `/research/manage?lang=en` 或 `lang=zh` |
| 全球态势 | 既有 `/global/`、`/en/global/` |

主站公开页面继续由 GitHub Pages 发布。Cloudflare Worker 仅接入账户、发布、
会话接口及账户静态资源。账户数据库继续使用已有服务器上的数据库，
不重新创建用户、不迁移到新数据库、不停用主站全球态势。
旧的 `global.residualinertia.com` 在后台作为现有服务来源保留，不作为主站账户入口。
此阶段未关闭旧域名，以免影响现有全球态势嵌入及数据服务。

## 语言与权限

- 主站 HTML 的语言决定账户入口的 `lang` 参数。
- 账户页面优先读取显式 `lang=en|zh`，再读取安全的语言偏好 cookie。
- 登录、注册、邮箱保存、作者 MFA、报告表单、预览和退出保持当前语言。
- 返回首页、研究、市场、About、全球态势进入对应语言的主站页面。
- 同一份 CSS 同时用于中英文；研究标题、简介、PDF 和用户姓名不自动翻译。
- 作者仍须完成密码与 Authenticator 验证；读者没有发布或管理权限。
- 主域名表单只接受精确的主站 Origin，并且后端必须验证 Worker 的私有共享密钥。
- 主域名 cookie 为 Secure / HttpOnly，页面和会话接口禁用缓存。
- 登录状态是域名独立的，切换到主域名后需要重新登录；现有账户和 MFA 绑定保留。

## 上线顺序

1. 恢复部署密钥对当前 Windows 账户的读取权限，或提供同一服务器的有效部署凭据。
   现有路径为 `E:/QuantResearchHub/deployment_credentials/ri-global/id_ed25519`。
   不在聊天中粘贴私钥，不向 Everyone 授权读取。
2. 在后端仓库生成并部署账户专用补丁，只更新 `account_locale.py`、`account_views.py`、
   `cloud_server.py`、`research_publisher.py`。不要使用完整 Global 发布包覆盖其他未发布改动。
   先备份这些文件；保留 `/opt/global-pulse/data`、已有环境配置和发布凭据。
3. 生成一个至少 32 字符的随机密钥，将同一值安全配置为后端 `RI_ACCOUNT_PROXY_SECRET`
   和 Worker secret `ACCOUNT_PROXY_SECRET`。不提交到 Git，也不输出到部署日志。
   只增加环境变量，保留既有 `RI_PUBLIC_ORIGIN` 和 `RI_PROXY_SECRET`。
4. 重启后端，验收旧入口的英文登录、注册、账户、作者 MFA、报告管理与中文回切。
5. 由域名所有者完成 Cloudflare 本机登录授权，或在 Cloudflare 控制台部署后端仓库
   `deployment/main-account/` 中的 Worker。使用 Routes，不使用全域 Custom Domain 接管。
6. 主域名现有 GitHub Pages DNS 记录开启代理，保留原记录的地址。SSL 使用 Full (strict)，
   不使用 Flexible。先记录现有配置，以便恢复。
7. 只添加 `wrangler.jsonc` 列出的账户路由；不得添加 `residualinertia.com/*`。
   为账户路由设置缓存绕过，不缓存 HTML、POST、cookie 或会话接口。
8. 在真实主域名完成下面的上线验收。
9. 主站 `site.json` 增加 `"accountServiceOrigin": "https://residualinertia.com"`，
   再构建、检查并发布。本次在主域名网关线上验收通过后启用此配置。

Cloudflare Routes 需要主机名对应的 DNS 开启代理；参考
[官方 Routes 文档](https://developers.cloudflare.com/workers/configuration/routing/routes/)。
密钥使用 [Wrangler secret](https://developers.cloudflare.com/workers/wrangler/commands/#secret-put)
或控制台 Secret binding 保存，不放在普通环境变量明文配置或代码中。

## 上线验收

- `/auth/login?lang=en`、`/auth/register?lang=en`：英文 HTML，主站资源 URL，主站表单 action。
- `/account?lang=en` 未登录重定向至主站英文登录，而非外部域名。
- 实际登录 / MFA 后账户、报告管理、PDF 预览保持主域名与语言。
- 读者无法进入报告管理；无效 Origin、缺失共享密钥、无效 CSRF 均被拒绝。
- 退出后 `/api/research/session` 显示未登录，主导航恢复英文登录入口。
- 主站首页、中英文研究、市场、About、全球态势仍正常；公开页面 canonical、
  hreflang、robots、sitemap 不回退。账户页面保持 noindex，不进入 sitemap。
- 账户返回导航不出现单独 Global 网站的管理入口。

## 回滚

先把主站 `accountServiceOrigin` 恢复为 `https://global.residualinertia.com` 并发布，
确认入口可用，再移除本次 Worker 账户路由。如果需要回滚后端，恢复本次备份的代码文件
并重启；不要恢复或覆盖账户数据库。只有本次确实更改了 DNS 代理时，才恢复其之前状态。

## 本机验证

主站：production build、32 个 Python 测试、6 项 JavaScript 验收、公开输出和链接检查通过。
后端：72 个测试全部通过，包含真实 Git 的临时本地仓库发布测试；
该测试禁用网络 Git 协议，不向 GitHub 发布测试内容。
Worker 路由 / Origin / cookie / 请求转发测试通过。
浏览器：10 个中英文桌面与移动页面检查通过，无横向溢出或运行错误。
仓库没有独立 lint/typecheck 命令；使用 Python 编译检查、JavaScript 语法检查及现有测试。
上述测试是本机结果；生产检查范围见本页状态，不能代替本人真实账户与 MFA 验收。
