# Motrix 2.4.2 — macOS 12 兼容版（不含 ED2K 改动）

这是 [agalwood/Motrix](https://github.com/agalwood/Motrix) v2.4.2 的 macOS 12 兼容分支。**本版本不包含任何 ED2K 识别或下载改动**，ED2K 行为与原版完全一致（原版不支持 ED2K）。

原作者：Dr_rOot / agalwood。原项目许可证：MIT。本分支遵循同一许可证。

## 本版相对原版改了什么

原版 2.4.2 的 Intel 安装包要求 macOS 13+，在 macOS 12 上无法启动。本分支只做兼容性修补：

1. `Info.plist` 的 `LSMinimumSystemVersion`：`13.0` → `12.0`。
2. 包内 18 个 Mach-O 文件的 `LC_BUILD_VERSION.minos`：`13.0` → `12.0`（脚本：`macos12-patch/patch_minos.py`）。
3. 用轻量转发/替身动态库补齐 3 个 macOS 13 才存在的符号：
   - `SMAppService`（ServiceManagement）→ 登录项注册功能在 macOS 12 上不可用；
   - `kVTCompressionPropertyKey_ReferenceBufferCount`（VideoToolbox）；
   - `NSPreviewRepresentingActivityItem`（AppKit）。
4. 主程序与所有独立辅助程序（`motrix-native-host`、`motrix-finalize-fs`、`MotrixSafariBootstrap`）逐个 ad-hoc 重签名。
   - 这一步很关键：若辅助程序未重签，启动会报 `spawn Unknown system error -85`，界面显示"任务暂不可用"。
5. 移除隔离属性（quarantine）。

补丁脚本在 `macos12-patch/`，包含 `patch_minos.py`、`weakify.py`、`fix_loop.py`、`stub.m`、`stub_vt.c`。

## 使用说明

1. 从 Releases 下载 `Motrix-2.4.2-macos12-x64.dmg`。
2. 打开 DMG，把 Motrix 拖进「应用程序」。
3. 首次打开若被 Gatekeeper 拦截，右键 →「打开」。
4. **不要使用应用内自动更新**：更新会覆盖修补文件并重新要求 macOS 13。

## 已验证环境

- macOS 12.7.6，Intel Xeon E3-1505M v5。
- 应用启动正常，仪表板显示「引擎 就绪」，aria2 v1.37.0 进程与 RPC 正常，无新增错误日志。
- HTTP/HTTPS 下载任务可正常创建。

## 许可证与致谢

- 原始项目 © Dr_rOot / agalwood，MIT License（见 `LICENSE`）。
- 本分支的修改同样以 MIT License 发布。
- 上游项目地址：https://github.com/agalwood/Motrix
