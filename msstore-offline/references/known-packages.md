# 常见 Microsoft Store 扩展 ProductID

下表已用 `scripts/msstore_fetch.py` 逐个实测通过（2026-10，通道 Retail）。
版本号会随时间变化，以脚本当次输出为准。

| 扩展 | ProductID | 包名主体 | 实测版本 |
|---|---|---|---|
| AV1 视频扩展 | `9MVZQVXJBQ9V` | `Microsoft.AV1VideoExtension` | 2.0.35.0 |
| HEVC 视频扩展（付费版） | `9NMZLZ57R3T7` | `Microsoft.HEVCVideoExtensions` | 2.4.151.0 |
| HEVC 视频扩展（设备制造商免费版） | `9N4WGH0Z6VHQ` | `Microsoft.HEVCVideoExtension` | 2.5.48.0 |
| VP9 视频扩展 | `9N4D0MSMP0PT` | `Microsoft.VP9VideoExtensions` | 1.2.20.0 |
| Web 媒体扩展 | `9N5TDP8VCMHS` | `Microsoft.WebMediaExtensions` | 含依赖包 |
| Webp 图像扩展 | `9PG2DK419DRG` | `Microsoft.WebpImageExtension` | 1.2.31.0 |
| 原始图像扩展 | `9NCTDW2W1BH8` | `Microsoft.RawImageExtension` | 含依赖包 |

注意两点：

1. **HEVC 有两个 ID**。`9N4WGH0Z6VHQ` 是「设备制造商版」，免费但只在 OEM 预装授权的机器上可装；
   `9NMZLZ57R3T7` 是付费版。两者包名相近但不同（`HEVCVideoExtension` vs `HEVCVideoExtensions`），别搞混。
2. **Web 媒体扩展、原始图像扩展会返回多个包**，其中包含 `Microsoft.VCLibs.140.00` 依赖。
   这类情况必须把依赖包一起下载，安装时用 `-DependencyPath` 指向依赖包所在目录：

```bat
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-AppxPackage -Path 'C:\dl\Microsoft.WebMediaExtensions_x.x.x.x_neutral_~_8wekyb3d8bbwe.appxbundle' -DependencyPath 'C:\dl\Microsoft.VCLibs.140.00_14.0.33519.0_x64__8wekyb3d8bbwe.appx'"
```

可以用 `--filter` 只看某一架构的包，例如 `--filter x64`。

## 查其他应用的 ProductID

商店网页地址末段就是 ProductID：`https://apps.microsoft.com/detail/9mvzqvxjbq9v` → `9MVZQVXJBQ9V`。
脚本也接受完整链接直接粘贴。
