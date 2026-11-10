# 部署说明

线上地址：**<https://curiosity.raricy.com>**

纯静态站点，没有后端、没有构建步骤；更新后不需要重启任何服务。

## 服务器

| 项 | 值 |
|---|---|
| 主机 | `cmsw`（SSH 别名，root 登录） |
| 站点目录 | `/root/raricynew/curiosities` |
| 仓库 | `git@github.com:raricycms/cabinet-of-curiosities.git`（SSH，shallow clone） |
| Web 服务 | nginx 1.20.1（Alibaba Cloud Linux 3） |

nginx 以 `nginx` 用户运行；`/root` 上已用 ACL 给 `nginx` 单独的 `--x` 穿行权限，站点目录本身是 `755`。

## nginx

配置文件：`/etc/nginx/conf.d/60-curiosity.raricy.com.conf`

- `root /root/raricynew/curiosities;`
- `index 00_从这里开始.html index.html;`（根路径直接是门户）
- 隐藏文件（`.git`、`.gitignore`、`.nojekyll`）一律 `403`
- 图片 / WAV / PDF 缓存 7 天，且关闭 gzip
- HTTP 全量 301 跳 HTTPS

改完配置后：

```bash
nginx -t && systemctl reload nginx
```

## HTTPS

- Let's Encrypt 证书，由 `certbot --nginx -d curiosity.raricy.com --redirect` 签发
- 证书位置：`/etc/letsencrypt/live/curiosity.raricy.com/`
- 自动续期：`certbot-renew.timer`（systemd timer）；可用 `certbot renew --dry-run` 验证

## 更新站点

```bash
ssh cmsw
cd /root/raricynew/curiosities
git pull
```

静态文件即时生效，无需 reload。

## 首次部署记录（2026-11-10）

1. `git clone --depth 1 git@github.com:raricycms/cabinet-of-curiosities.git /root/raricynew/curiosities`
2. 新建 `/etc/nginx/conf.d/60-curiosity.raricy.com.conf`，`nginx -t && systemctl reload nginx`
3. `certbot --nginx -d curiosity.raricy.com --redirect --non-interactive --agree-tos`
4. 验证：根路径 200、HTTP 301、`.git` 403、12 个展品页与 WAV / PDF / 海报均 200
