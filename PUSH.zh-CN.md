# 推送到 GitHub（私有仓库）

本地仓库、commit、全部文件都已备好，只差推上去。GitHub 应用没有建仓权限，所以建仓库这一步需要你在网页点两下（1 分钟），然后跑一条命令。

## 第 1 步：在 GitHub 建一个空仓库

1. 打开 <https://github.com/new>，登录你的账号 **Ban404**。
2. Repository name 填：`jst-query-helper`
3. 选 **Private**（私有，符合你的选择）。
4. **不要**勾选 "Add a README"、".gitignore"、"license"——保持完全空白（本地已有这些文件）。
5. 点 **Create repository**。

## 第 2 步：推送（选一种）

建好后页面会显示地址。在终端进入本仓库目录，二选一：

### 方式 A：HTTPS + Personal Access Token（推荐，不用配 SSH）

先去 <https://github.com/settings/tokens> → Generate new token (classic) → 勾 `repo` 权限 → 生成并复制 token（只显示一次）。

先进入本仓库文件夹（终端里 `cd` 到这个 `jst-query-helper` 目录），然后：

```bash
git remote add origin https://Ban404:<你的token>@github.com/Ban404/jst-query-helper.git
git push -u origin master
```

> 推送成功后建议立刻改回不带 token 的地址，避免 token 留在 `.git/config`：
> `git remote set-url origin https://github.com/Ban404/jst-query-helper.git`

### 方式 B：SSH（如果你已配过 GitHub SSH key）

先进入本仓库文件夹，然后：

```bash
git remote add origin git@github.com:Ban404/jst-query-helper.git
git push -u origin master
```

## 第 3 步：确认

刷新 GitHub 仓库页面，应看到三套目录（`skill/` `connector/` `mcp/`）、README 已渲染、最新 commit 是三套独立发行版。CI（`.github/workflows/ci.yml`）会自动跑起来。

## 以后改成公开

你确认没问题后，在仓库 **Settings → General → Danger Zone → Change visibility → Public** 即可。项目已含免责声明、安全策略、MIT 许可，公开前建议再扫一遍：`python tools/scan_secrets.py`。

## 想先本地看一眼再推

```bash
git log --stat -1        # 看这次提交改了什么
git ls-files | wc -l     # 当前追踪文件数（三套 + 文档 + 工具）
```
