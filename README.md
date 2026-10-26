# msstore-offline

不打开 Microsoft Store，直接从微软官方分发接口取回 appx / msixbundle 安装包并本地安装。

面向的场景很具体：**Microsoft Store 打不开或报错，但你需要装一个商店里的扩展**
（AV1 / HEVC / VP9 视频扩展、Web 媒体扩展等）。

取回的包来自 `tlu.dl.delivery.mp.microsoft.com`——微软官方 CDN，带微软数字签名，
不是第三方重打包，安装后校验摘要。

## 安装

作为 Agent Skill 安装（Claude Code / Cursor / Codex / WorkBuddy 等）：

```bash
npx skills add Bluemohb/msstore-offline
```

或手动复制：把 `msstore-offline/` 整个目录放到你的 skills 目录下
（WorkBuddy 为 `~/.workbuddy-ai/skills/`，其它客户端见各自文档）。

不需要安装任何 Python 包，脚本只用标准库。

## 用法

```bash
# 只查询，不下载
python msstore-offline/scripts/msstore_fetch.py 9MVZQVXJBQ9V

# 查询并下载
python msstore-offline/scripts/msstore_fetch.py 9MVZQVXJBQ9V --download --out ./dl

# 只看某一架构
python msstore-offline/scripts/msstore_fetch.py 9MVZQVXJBQ9V --download --filter x64
```

ProductID 就是商店链接末段：`apps.microsoft.com/detail/9mvzqvxjbq9v` → `9MVZQVXJBQ9V`。

已验证的常见扩展：

| 扩展 | ProductID |
|---|---|
| AV1 视频扩展 | `9MVZQVXJBQ9V` |
| HEVC 视频扩展（付费） | `9NMZLZ57R3T7` |
| HEVC 视频扩展（OEM 免费） | `9N4WGH0Z6VHQ` |
| VP9 视频扩展 | `9N4D0MSMP0PT` |
| Web 媒体扩展 | `9N5TDP8VCMHS` |
| Webp 图像扩展 | `9PG2DK419DRG` |
| 原始图像扩展 | `9NCTDW2W1BH8` |

安装用 `Add-AppxPackage`，不经过商店：

```bat
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-AppxPackage -Path 'C:\dl\xxx.appxbundle'"
```

也可以直接双击 `.appxbundle`，交给「应用安装程序」。

## 先确认你真的需要它

**mpv、VLC、ffmpeg 自带 dav1d 等解码器，AV1/HEVC 是原生支持的，不需要任何商店扩展。**
如果你的播放器是这几个却打不开文件，装扩展解决不了问题，先查版本和解码参数。

真正会提示「需要 AV1/HEVC 视频扩展」的是 Media Foundation 系应用：
Windows 媒体播放器、电影和电视、照片、部分浏览器与剪辑软件。

## 工作原理

模拟商店客户端，走 Windows Update 的 FE3 服务：

1. `GetCookie` — 取匿名票据
2. Storefront 接口 — 由 ProductID 查 `WuCategoryId`
3. `SyncUpdates` — 拉该分类下的包清单（名称、大小、摘要）
4. `GetExtendedUpdateInfo2` — 换取 CDN 真实直链

细节与踩过的坑见 `msstore-offline/references/pitfalls.md`。

## 已知限制

- **用的是微软未公开的接口。** 小范围使用很稳定，但微软随时可能改动，不保证长期可用。
- **内置的匿名设备票据是全生态共用的。** 用的人越多越容易被限流。
  遇到 500 / `InvalidSecurity`，用 `--device-token` 或环境变量 `MSSTORE_DEVICE_TOKEN` 换一个。
- **下载必须校验。** CDN 在限流时会返回一个 150 字节的 `403` HTML 页，
  状态码还可能是 200，文件名也正常。脚本会自动比对大小与摘要，不要绕过。
- **版本号和 ProductID 会变。** 表里的版本仅供参考。

## 许可

代码以 MIT 发布，见 `LICENSE`。
内置的设备票据常量来自 StoreLib（MPL-2.0），出处与许可说明见 `THIRD-PARTY-NOTICES.md`。

本项目与 Microsoft Corporation 无隶属关系。
