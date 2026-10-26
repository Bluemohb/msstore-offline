# 第三方声明

本项目主体（`msstore-offline/SKILL.md`、`references/` 以及
`scripts/msstore_fetch.py` 的实现代码）以 MIT 许可证发布，见 `LICENSE`。

以下内容并非原创，单独列出。

---

## 1. 匿名设备票据常量

`msstore-offline/scripts/msstore_fetch.py` 中的 `DEFAULT_DEVICE_TOKEN`
（2008 字符的 base64 字符串）与下列项目中的常量逐字节相同：

- 项目：**StoreLib**
- 仓库：https://github.com/StoreDev/StoreLib
- 文件：`StoreLib/Services/FE3Handler.cs`，第 21 行 `_msaToken`
- 许可证：**Mozilla Public License 2.0 (MPL-2.0)**
- 许可证全文：https://www.mozilla.org/en-US/MPL/2.0/

说明：

- 该常量是 Windows Update 的**匿名设备票据**，不含任何个人身份信息，
  不属于某位开发者的账号凭据。它在多个开源 Microsoft Store 下载工具中公开流通。
- MPL-2.0 的传染范围以**文件**为单位，仅作用于被修改的 MPL 源文件。
  本项目未修改 StoreLib 的任何源文件，仅在新写的 Python 文件中引用了该常量值，
  因此 `msstore_fetch.py` 仍按 MIT 发布，此处按 MPL-2.0 要求保留出处与许可声明。
- 若你认为该引用方式不妥，可通过环境变量 `MSSTORE_DEVICE_TOKEN`
  或命令行参数 `--device-token` 提供自己的票据，脚本内置默认值将被完全覆盖。

## 2. FE3 协议请求结构

SOAP 请求模板（`GetCookie` / `SyncUpdates` / `GetExtendedUpdateInfo2` 的元素顺序与字段）
参考了以下实现的公开代码：

- StoreLib — https://github.com/StoreDev/StoreLib （MPL-2.0）
- CodexDesktop-Rebuild — https://github.com/Haleclipse/CodexDesktop-Rebuild

模板本身是对微软未公开接口的调用格式还原，不含上述项目的独创性表达；
本项目按 MIT 发布。

## 3. 商标

Microsoft、Windows、Microsoft Store 是 Microsoft Corporation 的商标。
本项目与 Microsoft Corporation 无隶属关系，也未获其认可。
