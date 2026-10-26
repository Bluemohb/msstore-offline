# 协议细节与踩坑记录

## FE3 四步流程

服务端点：`https://fe3.delivery.mp.microsoft.com/ClientWebService/client.asmx`
取直链的那一步用 `/secured` 后缀。

1. **GetCookie** — `<GetCookie><WindowsUpdateType>Others</WindowsUpdateType></GetCookie>`
   匿名票据用 `<TicketType Name="MSA" ...><User/></TicketType>` 即可。
   返回的 `<Expiration>` 常是 `0001-04-01T00:00:00Z` 这种占位值，**不能直接用**；
   SyncUpdates 里用固定值 `2045-03-11T02:02:48Z` 会被接受。

2. **产品信息** — 走 Storefront 接口，不走 FE3：
   `https://storeedgefd.dsx.mp.microsoft.com/v9.0/products/{pid}?market=US&locale=en-US&deviceFamily=Windows.Desktop`
   从 `Payload.Skus[0].FulfillmentData`（是个 JSON 字符串）里取 `WuCategoryId`。
   取不到就说明该产品不是 appx/msix 打包。

3. **SyncUpdates** — 三个必踩的坑：
   - **必须带消息级安全头**：`<o:Security>` + `<Timestamp>` + `<wuws:WindowsUpdateTicketsToken>`，
     其中 `TicketType` 里放 `<Device>` 匿名设备票据（约 2KB base64）。漏了直接 500 `InvalidSecurity`。
   - **`InstalledNonLeafUpdateIDs` 要用 `<int>` 子元素**，不能写成重复的同名元素。
   - `DeviceAttributes` / `CallerAttributes` 是**分号分隔的单串**，不是子元素：
     `FlightRing=Retail;DeviceFamily=Windows.Desktop;` 和 `Interactive=1;IsSeeker=0;`

4. **GetExtendedUpdateInfo2** — 传上一步拿到的 `UpdateID` + `RevisionNumber`，
   `infoTypes` 要 `FileUrl` 和 `FileDecryption`，返回的 `FileLocation` 里
   `FileDigest` 与上一步的 `Digest` 对上即为该包的真实 URL。

## 响应解析的两个反直觉点

- `<Xml>` 里是 **XML 转义的内联片段**（`&lt;UpdateIdentity .../&gt;`），**不是 base64**。
  要先把 `&lt;` `&gt;` `&quot;` `&apos;` 反转义再解析；`&amp;` **不要动**，否则内层属性里的 `&` 会被提前解码导致解析失败。
- `<File FileName="...">` 的 `FileName` 只是 CDN 上的**哈希文件名**（`<guid>.appxbundle`）。
  真实文件名要用 `AppxMetadata@PackageMoniker` **加** `FileName` 的扩展名拼出来。
  `PackageMoniker` 与 `File@InstallerSpecificIdentifier` 是同一个值，用它做关联。

## 下载

- **必须用 `http://`**，不要升级成 https。该 CDN 在本机经代理访问时 https 直接连不通（curl 返回 000），
  http 正常返回 200 与完整字节数。
- 直链带 `P1/P2/P3/P4` 时效参数，**每次都要重新取**，不要复用旧 URL。
- **重复请求会触发限流**，返回一个 **150 字节的 `403 Forbidden`（openresty）HTML 页**。
  这个错误页状态码可能是 200，文件名也对，极易误判成下载成功。必须比对大小 + 摘要。
- FE3 的 `Digest` 是 **base64 编码的 SHA-1**（20 字节）。若 base64 解码后是 32 字节则为 SHA-256。
  脚本按长度自适应选择算法。

## TLS 与代理

- `fe3.delivery.mp.microsoft.com` **不发送中间 CA 证书**，标准信任链建不起来，
  Node 的 `https` 和 Python 的 `urllib` 都会报证书错误。脚本用 `ssl.CERT_NONE` 关闭校验。
  这是可接受的：取的是公开元数据和微软签名安装包，且下载后校验摘要。
- Python `urllib` 会读取 `http_proxy` / `https_proxy` 环境变量并走代理；Node 的 `https` **不会**，
  这也是同一台机器上 Node 直连、curl 走代理的原因。排查网络问题时先确认这一点。
- 若用 Node 版本（`ref_fetch.js` 类实现），`downloadFile` 必须按 URL 协议选择 `http` / `https` 模块，
  统一用 `https.get` 会因为 URL 是 http 而报 `Protocol "http:" not supported`。

## 安装侧

- `Add-AppxPackage` 是唯一不碰商店的安装入口。
- Agent 沙箱常禁止从 shell 调 `powershell.exe`（安全策略会直接拒绝），此时只能生成 `.cmd` 交给用户。
  `.cmd` 内含中文时必须存成 **GBK**，否则 `chcp 936` 下显示乱码。
- `.appxbundle` 双击会交给「应用安装程序」（Microsoft.DesktopAppInstaller）处理。
  winget 存在即说明该组件在，双击是可用的兜底路径。
- 验证是否装好：`C:\Program Files\WindowsApps` 受 ACL 保护，普通用户 `ls` 会被拒绝，
  不要据此判断"没装上"。让用户看「设置 → 应用 → 已安装的应用」，或直接试播文件。
