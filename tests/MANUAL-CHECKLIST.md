# 手动核查清单

以下发现无法用单元测试覆盖，须人工执行并记录结果。

**本清单不计入测试覆盖率。** 报告完成度时须与自动化测试结果分开声明。

---

## 1. UAC 提权参数转发

- [ ] 以 `安装器.exe -platformpluginpath C:\Users\Public\evil` 启动，同意 UAC
- [ ] 确认提权后的进程**未**从该目录加载 DLL
- [ ] 确认安装路径含空格（如 `C:\Program Files\...`）时提权仍能正常启动
- [ ] 确认用户拒绝 UAC 时程序给出明确提示而非静默退出

对应发现：`utils/helpers.py:465`

## 2. 三处裸文件名的 PATH 劫持

- [ ] 在安装器同目录放置无害的 `curl.exe`，点击「IPv6 连接测试」，确认**未**执行该文件
- [ ] 同样方式验证 `taskkill.exe`（取消下载时触发）
- [ ] 同样方式验证 `powershell.exe`（菜单「打开 hosts 文件」时触发）

对应发现：`ipv6_manager.py:93,238`、`download.py:53`、`ui_manager.py:262`

## 3. CI 标签注入

- [ ] 推送形如 `v0.0.0-test-$(Get-Date)` 的标签到测试仓库
- [ ] 确认 runner 上**未**执行该子表达式
- [ ] 已确认前提：`git check-ref-format` 接受 `$(Get-Date)` 与 `v1.0";calc;"` 两种形式

对应发现：`.github/workflows/build-release.yml:31`

## 4. 打包产物是否仍包含 .py 源码

- [ ] 用 7-Zip 或 `pyinstxtractor` 解开发布的 exe
- [ ] 确认其中**不含** `core/`、`utils/`、`workers/`、`ui/`、`config/` 下的 `.py` 文件

对应发现：`source/build.spec:29-36`

## 5. 内置两个 exe 的签名状态

- [ ] `Get-AuthenticodeSignature source/bin/aria2c-fast_x64.exe`
- [ ] `Get-AuthenticodeSignature source/bin/cfst.exe`
- [ ] 记录结果，并在仓库中登记两者的上游版本号与 SHA-256

对应发现：`source/bin/` 二进制无校验记录

## 6. 发布产物是否附带 SHA-256

- [ ] 确认 Release 页面存在 `.sha256` 文件
- [ ] 确认其内容与实际 exe 的哈希一致

对应发现：`.github/workflows/build-release.yml` 无校验和步骤

## 7. 真实网络环境下的证书校验行为

- [ ] 在启用 Cloudflare 优选（已改写 hosts）的情况下执行一次完整下载
- [ ] 确认证书校验开启时握手成功
- [ ] 若握手失败，确认程序回退为「放弃优选 + 直连重试」，而**不是**关闭证书校验

对应发现：`workers/download.py:214`

> **注**：Spec §11 验收标准第 6 条写「覆盖全部 10 条无法自动化的发现」，而 §9 正文只列出 7 项。本清单以 §9 正文的 7 项为准。该计数差异已记录，若后续确认存在遗漏项，追加到本文件即可。
