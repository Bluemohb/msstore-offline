#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从微软官方分发接口获取 Microsoft Store 应用包直链并下载。

只依赖 Python 标准库。原理是模拟商店客户端走 Windows Update 的 FE3 服务：
    GetCookie -> 产品信息(WuCategoryId) -> SyncUpdates(包清单) -> GetExtendedUpdateInfo2(直链)

用法:
    python msstore_fetch.py 9MVZQVXJBQ9V
    python msstore_fetch.py 9MVZQVXJBQ9V --download --out ./dl
    python msstore_fetch.py 9MVZQVXJBQ9V --download --filter x64 --json
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

FE3 = "https://fe3.delivery.mp.microsoft.com/ClientWebService/client.asmx"
FE3_SECURED = FE3 + "/secured"
NS = "http://www.microsoft.com/SoftwareDistribution/Server/ClientWebService"
PRODUCT_API = "https://storeedgefd.dsx.mp.microsoft.com/v9.0/products/{pid}?market={market}&locale={locale}&deviceFamily=Windows.Desktop"

UA = "Windows-Update-Agent/10.0.10011.16384 Client-Protocol/2.40"
DEFAULT_EXPIRY = "2045-03-11T02:02:48Z"

# 匿名设备票据。FE3 的 WindowsUpdateTicketsToken 里必须有 Device 票据：
# 填空的 <User/> 只会拿到占位过期时间 0001-04-01，随后 SyncUpdates 报
# 500 InvalidSecurity。该票据由 Windows Update 客户端在设备注册时下发，
# 没有公开的签发接口，无法自行生成。
#
# 下面的默认值与开源库 StoreLib 的 FE3Handler.cs 中 _msaToken 逐字节相同：
#   https://github.com/StoreDev/StoreLib/blob/master/StoreLib/Services/FE3Handler.cs
# StoreLib 以 MPL-2.0 发布，出处与许可声明见仓库根目录 THIRD-PARTY-NOTICES.md。
# 该票据为全生态共用的匿名配额，被限流时可用 MSSTORE_DEVICE_TOKEN 覆盖。
DEFAULT_DEVICE_TOKEN = "dAA9AEUAdwBBAHcAQQBzAE4AMwBCAEEAQQBVADEAYgB5AHMAZQBtAGIAZQBEAFYAQwArADMAZgBtADcAbwBXAHkASAA3AGIAbgBnAEcAWQBtAEEAQQBMAGoAbQBqAFYAVQB2AFEAYwA0AEsAVwBFAC8AYwBDAEwANQBYAGUANABnAHYAWABkAGkAegBHAGwAZABjADEAZAAvAFcAeQAvAHgASgBQAG4AVwBRAGUAYwBtAHYAbwBjAGkAZwA5AGoAZABwAE4AawBIAG0AYQBzAHAAVABKAEwARAArAFAAYwBBAFgAbQAvAFQAcAA3AEgAagBzAEYANAA0AEgAdABsAC8AMQBtAHUAcgAwAFMAdQBtAG8AMABZAGEAdgBqAFIANwArADQAcABoAC8AcwA4ADEANgBFAFkANQBNAFIAbQBnAFIAQwA2ADMAQwBSAEoAQQBVAHYAZgBzADQAaQB2AHgAYwB5AEwAbAA2AHoAOABlAHgAMABrAFgAOQBPAHcAYQB0ADEAdQBwAFMAOAAxAEgANgA4AEEASABzAEoAegBnAFQAQQBMAG8AbgBBADIAWQBBAEEAQQBpAGcANQBJADMAUQAvAFYASABLAHcANABBAEIAcQA5AFMAcQBhADEAQgA4AGsAVQAxAGEAbwBLAEEAdQA0AHYAbABWAG4AdwBWADMAUQB6AHMATgBtAEQAaQBqAGgANQBkAEcAcgBpADgAQQBlAEUARQBWAEcAbQBXAGgASQBCAE0AUAAyAEQAVwA0ADMAZABWAGkARABUAHoAVQB0AHQARQBMAEgAaABSAGYAcgBhAGIAWgBsAHQAQQBUAEUATABmAHMARQBGAFUAYQBRAFMASgB4ADUAeQBRADgAagBaAEUAZQAyAHgANABCADMAMQB2AEIAMgBqAC8AUgBLAGEAWQAvAHEAeQB0AHoANwBUAHYAdAB3AHQAagBzADYAUQBYAEIAZQA4AHMAZwBJAG8AOQBiADUAQQBCADcAOAAxAHMANgAvAGQAUwBFAHgATgBEAEQAYQBRAHoAQQBYAFAAWABCAFkAdQBYAFEARQBzAE8AegA4AHQAcgBpAGUATQBiAEIAZQBUAFkAOQBiAG8AQgBOAE8AaQBVADcATgBSAEYAOQAzAG8AVgArAFYAQQBiAGgAcAAwAHAAUgBQAFMAZQBmAEcARwBPAHEAdwBTAGcANwA3AHMAaAA5AEoASABNAHAARABNAFMAbgBrAHEAcgAyAGYARgBpAEMAUABrAHcAVgBvAHgANgBuAG4AeABGAEQAbwBXAC8AYQAxAHQAYQBaAHcAegB5AGwATABMADEAMgB3AHUAYgBtADUAdQBtAHAAcQB5AFcAYwBLAFIAagB5AGgAMgBKAFQARgBKAFcANQBnAFgARQBJADUAcAA4ADAARwB1ADIAbgB4AEwAUgBOAHcAaQB3AHIANwBXAE0AUgBBAFYASwBGAFcATQBlAFIAegBsADkAVQBxAGcALwBwAFgALwB2AGUATAB3AFMAawAyAFMAUwBIAGYAYQBLADYAagBhAG8AWQB1AG4AUgBHAHIAOABtAGIARQBvAEgAbABGADYASgBDAGEAYQBUAEIAWABCAGMAdgB1AGUAQwBKAG8AOQA4AGgAUgBBAHIARwB3ADQAKwBQAEgAZQBUAGIATgBTAEUAWABYAHoAdgBaADYAdQBXADUARQBBAGYAZABaAG0AUwA4ADgAVgBKAGMAWgBhAEYASwA3AHgAeABnADAAdwBvAG4ANwBoADAAeABDADYAWgBCADAAYwBZAGoATAByAC8ARwBlAE8AegA5AEcANABRAFUASAA5AEUAawB5ADAAZAB5AEYALwByAGUAVQAxAEkAeQBpAGEAcABwAGgATwBQADgAUwAyAHQANABCAHIAUABaAFgAVAB2AEMAMABQADcAegBPACsAZgBHAGsAeABWAG0AKwBVAGYAWgBiAFEANQA1AHMAdwBFAD0AJgBwAD0A"

# 运行时生效的票据，可被环境变量或 --device-token 覆盖
DEVICE_TOKEN = DEFAULT_DEVICE_TOKEN

# FE3 服务端不发送中间 CA 证书，标准信任链无法建立，故关闭校验。
# 通信内容为公开的商店元数据与微软签名的安装包，且下载后会校验 SHA256。
TLS = ssl.create_default_context()
TLS.check_hostname = False
TLS.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------- XML 辅助

def _local(tag):
    return tag.rsplit("}", 1)[-1]


def find_local(root, name):
    for e in root.iter():
        if _local(e.tag) == name:
            return e
    return None


def findall_local(root, name):
    return [e for e in root.iter() if _local(e.tag) == name]


def text_of(root, name, default=""):
    e = find_local(root, name)
    if e is None or e.text is None:
        return default
    return e.text.strip()


# ---------------------------------------------------------------- HTTP

def _utc(delta=0):
    t = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delta)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def soap_post(url, body):
    req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/soap+xml; charset=utf-8")
    req.add_header("User-Agent", UA)
    try:
        with urllib.request.urlopen(req, timeout=90, context=TLS) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError("SOAP 请求失败 HTTP %s\n%s" % (e.code, detail[:1500]))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=TLS) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ---------------------------------------------------------------- SOAP 模板

COOKIE_BODY = """<s:Envelope xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:s="http://www.w3.org/2003/05/soap-envelope">
<s:Header>
<a:Action s:mustUnderstand="1">http://www.microsoft.com/SoftwareDistribution/Server/ClientWebService/GetCookie</a:Action>
<a:MessageID>urn:uuid:{mid}</a:MessageID>
<a:To s:mustUnderstand="1">{url}</a:To>
<o:Security s:mustUnderstand="1" xmlns:o="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
<Timestamp xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
<Created>{created}</Created><Expires>{expires}</Expires></Timestamp>
<wuws:WindowsUpdateTicketsToken wsu:id="ClientMSA" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wuws="http://schemas.microsoft.com/msus/2014/10/WindowsUpdateAuthorization">
<TicketType Name="MSA" Version="1.0" Policy="MBI_SSL"><User/></TicketType>
</wuws:WindowsUpdateTicketsToken>
</o:Security>
</s:Header>
<s:Body><GetCookie xmlns="{ns}"><WindowsUpdateType>Others</WindowsUpdateType></GetCookie></s:Body>
</s:Envelope>"""


def _security_header(created, expires):
    return """<o:Security s:mustUnderstand="1" xmlns:o="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
<Timestamp xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
<Created>{c}</Created><Expires>{e}</Expires></Timestamp>
<wuws:WindowsUpdateTicketsToken wsu:id="ClientMSA" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wuws="http://schemas.microsoft.com/msus/2014/10/WindowsUpdateAuthorization">
<TicketType Name="MSA" Version="1.0" Policy="MBI_SSL"><Device>{tok}</Device></TicketType>
</wuws:WindowsUpdateTicketsToken>
</o:Security>""".format(c=created, e=expires, tok=DEVICE_TOKEN)


SYNC_BODY = """<s:Envelope xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:s="http://www.w3.org/2003/05/soap-envelope">
<s:Header>
<a:Action s:mustUnderstand="1">http://www.microsoft.com/SoftwareDistribution/Server/ClientWebService/SyncUpdates</a:Action>
<a:MessageID>urn:uuid:{mid}</a:MessageID>
<a:To s:mustUnderstand="1">{url}</a:To>
{sec}
</s:Header>
<s:Body><SyncUpdates xmlns="{ns}">
<cookie><Expiration>{expiry}</Expiration><EncryptedData>{cookie}</EncryptedData></cookie>
<parameters>
<ExpressQuery>false</ExpressQuery>
<InstalledNonLeafUpdateIDs>
<int>1</int><int>2</int><int>3</int><int>11</int><int>19</int><int>544</int><int>549</int>
<int>2359974</int><int>2359977</int><int>5169044</int><int>8788830</int><int>23110993</int><int>23110994</int>
<int>54341900</int><int>54343656</int><int>59830006</int><int>59830007</int><int>59830008</int>
<int>60484010</int><int>62450018</int><int>62450019</int><int>62450020</int><int>66027979</int>
<int>66053150</int><int>97657898</int><int>98822896</int><int>98959022</int><int>98959023</int>
<int>98959024</int><int>98959025</int><int>98959026</int><int>104433538</int><int>104900364</int>
<int>105489019</int><int>117765322</int><int>129905029</int><int>130040031</int><int>132387090</int>
<int>132393049</int><int>133399034</int><int>138537048</int><int>140377312</int><int>143747671</int>
<int>158941041</int><int>158941042</int><int>158941043</int><int>158941044</int><int>159123858</int>
<int>159130928</int><int>164836897</int><int>164847386</int><int>164848327</int><int>164852241</int>
<int>164852246</int><int>164852252</int><int>164852253</int>
</InstalledNonLeafUpdateIDs>
<OtherCachedUpdateIDs></OtherCachedUpdateIDs>
<SkipSoftwareSync>false</SkipSoftwareSync>
<NeedTwoGroupOutOfScopeUpdates>true</NeedTwoGroupOutOfScopeUpdates>
<FilterAppCategoryIds><CategoryIdentifier><Id>{cat}</Id></CategoryIdentifier></FilterAppCategoryIds>
<TreatAppCategoryIdsAsInstalled>true</TreatAppCategoryIdsAsInstalled>
<AlsoPerformRegularSync>false</AlsoPerformRegularSync>
<ComputerSpec />
<ExtendedUpdateInfoParameters>
<XmlUpdateFragmentTypes><XmlUpdateFragmentType>Extended</XmlUpdateFragmentType></XmlUpdateFragmentTypes>
</ExtendedUpdateInfoParameters>
<ProductsParameters>
<SyncCurrentVersionOnly>false</SyncCurrentVersionOnly>
<DeviceAttributes>FlightRing={ring};DeviceFamily=Windows.Desktop;</DeviceAttributes>
<CallerAttributes>Interactive=1;IsSeeker=0;</CallerAttributes>
<Products />
</ProductsParameters>
</parameters>
</SyncUpdates></s:Body>
</s:Envelope>"""


URL_BODY = """<s:Envelope xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:s="http://www.w3.org/2003/05/soap-envelope">
<s:Header>
<a:Action s:mustUnderstand="1">http://www.microsoft.com/SoftwareDistribution/Server/ClientWebService/GetExtendedUpdateInfo2</a:Action>
<a:MessageID>urn:uuid:{mid}</a:MessageID>
<a:To s:mustUnderstand="1">{url}</a:To>
{sec}
</s:Header>
<s:Body>
<GetExtendedUpdateInfo2 xmlns="{ns}">
<updateIDs><UpdateIdentity><UpdateID>{uid}</UpdateID><RevisionNumber>{rev}</RevisionNumber></UpdateIdentity></updateIDs>
<infoTypes><XmlUpdateFragmentType>FileUrl</XmlUpdateFragmentType><XmlUpdateFragmentType>FileDecryption</XmlUpdateFragmentType></infoTypes>
<deviceAttributes>FlightRing={ring};DeviceFamily=Windows.Desktop;</deviceAttributes>
</GetExtendedUpdateInfo2>
</s:Body>
</s:Envelope>"""


# ---------------------------------------------------------------- 四个步骤

def new_mid():
    import uuid
    return uuid.uuid4()


def get_cookie():
    body = COOKIE_BODY.format(mid=new_mid(), url=FE3, ns=NS, created=_utc(-60), expires=_utc(300))
    resp = soap_post(FE3, body)
    root = ET.fromstring(resp)
    cookie = text_of(root, "EncryptedData")
    if not cookie:
        raise RuntimeError("GetCookie 未返回 EncryptedData：\n" + resp[:1200])
    expiry = text_of(root, "Expiration")
    # 匿名票据常返回 0001-04-01 这种占位时间，此时用 FE3 接受的固定值
    if not re.match(r"^(19|20)\d\d-", expiry or ""):
        expiry = DEFAULT_EXPIRY
    return cookie, expiry


def get_product(product_id, market="US", locale="en-US"):
    data = get_json(PRODUCT_API.format(pid=product_id, market=market, locale=locale))
    payload = data.get("Payload") or {}
    category = ""
    for sku in payload.get("Skus") or []:
        fd = sku.get("FulfillmentData")
        if fd:
            try:
                category = json.loads(fd).get("WuCategoryId", "")
            except Exception:
                pass
            if category:
                break
    return {
        "product_id": product_id,
        "title": payload.get("Title", ""),
        "publisher": payload.get("PublisherName", ""),
        "category_id": category,
        "platforms": payload.get("Platforms") or [],
    }


def sync_updates(cookie, expiry, category_id, ring="Retail"):
    body = SYNC_BODY.format(
        mid=new_mid(), url=FE3, ns=NS, sec=_security_header(_utc(-60), _utc(300)),
        expiry=expiry, cookie=cookie, cat=category_id, ring=ring,
    )
    try:
        resp = soap_post(FE3, body)
    except RuntimeError as e:
        raise RuntimeError(
            "%s\n\n若是 500 / InvalidSecurity：内置的匿名设备票据可能已被限流，"
            "换一个再试（--device-token 或环境变量 MSSTORE_DEVICE_TOKEN）。" % e
        )

    # 响应里的 <Xml> 是 XML 转义的内联片段，反转义后才能当结构解析。
    # 注意保留 &amp;，否则内层属性里的 & 会被提前解码。
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        resp = resp.replace(a, b)
    root = ET.fromstring(resp)

    # 包体信息在 <File> 上，用 InstallerSpecificIdentifier 与 AppxMetadata 的
    # PackageMoniker 关联。
    files = {}
    for f in findall_local(root, "File"):
        key = f.get("InstallerSpecificIdentifier") or ""
        if key:
            files[key] = f

    packages = []
    for ui in findall_local(root, "UpdateInfo"):
        meta = None
        for e in ui.iter():
            if _local(e.tag) == "AppxMetadata":
                meta = e
                break
        if meta is None:
            continue
        moniker = meta.get("PackageMoniker") or ""
        if moniker not in files:
            continue

        ident = None
        for e in ui.iter():
            if _local(e.tag) == "UpdateIdentity":
                ident = e
                break
        if ident is None:
            continue

        f = files[moniker]
        # FileName 只是 CDN 上的哈希名（<guid>.appxbundle），真实文件名要用
        # PackageMoniker + 扩展名拼出来。
        cdn_name = f.get("FileName") or ""
        ext = cdn_name[cdn_name.rfind("."):] if "." in cdn_name else ""
        name = moniker + ext
        if not ext:
            continue
        packages.append({
            "name": name,
            "moniker": moniker,
            "size": int(f.get("Size") or 0),
            "digest": f.get("Digest") or "",
            "update_id": ident.get("UpdateID") or "",
            "revision": ident.get("RevisionNumber") or "",
        })
    return packages


def get_url(update_id, revision, ring, digest):
    body = URL_BODY.format(
        mid=new_mid(), url=FE3_SECURED, ns=NS, sec=_security_header(_utc(-60), _utc(300)),
        uid=update_id, rev=revision, ring=ring,
    )
    resp = soap_post(FE3_SECURED, body)
    root = ET.fromstring(resp)

    fallback = ""
    for loc in findall_local(root, "FileLocation"):
        d = text_of(loc, "FileDigest")
        u = text_of(loc, "Url")
        if not u:
            continue
        if d and digest and d == digest:
            return u
        if not fallback:
            fallback = u
    return fallback


# ---------------------------------------------------------------- 下载与校验

def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f %s" % (n, unit) if unit != "B" else "%d B" % n
        n /= 1024.0


def download(url, dest, expect_size=0, expect_digest=""):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(262144)
            if not chunk:
                break
            f.write(chunk)

    size = os.path.getsize(dest)
    if expect_size and size != expect_size:
        raise RuntimeError("大小不符：期望 %d，实际 %d（很可能是 CDN 返回的错误页）" % (expect_size, size))

    if expect_digest:
        # FE3 的 Digest 是 base64 摘要，长度 20 字节为 SHA-1、32 字节为 SHA-256
        try:
            raw = base64.b64decode(expect_digest)
        except Exception:
            raw = b""
        algo = "sha1" if len(raw) == 20 else "sha256" if len(raw) == 32 else ""
        if algo:
            h = hashlib.new(algo)
            with open(dest, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            got = base64.b64encode(h.digest()).decode()
            if got != expect_digest:
                raise RuntimeError(
                    "%s 校验不符：期望 %s，实际 %s（很可能是 CDN 返回的错误页）"
                    % (algo.upper(), expect_digest, got)
                )
    return size


# ---------------------------------------------------------------- 入口

def main(argv=None):
    ap = argparse.ArgumentParser(description="获取 Microsoft Store 应用包直链并下载（官方 FE3 分发接口）")
    ap.add_argument("product_id", help="商店产品 ID，如 9MVZQVXJBQ9V（也接受完整商店链接）")
    ap.add_argument("--ring", default="Retail", help="分发通道 Retail/RP/WIS/WIF，默认 Retail")
    ap.add_argument("--market", default="US", help="市场代码，默认 US")
    ap.add_argument("--locale", default="en-US", help="区域语言，默认 en-US")
    ap.add_argument("--download", action="store_true", help="下载找到的包")
    ap.add_argument("--out", default="./downloads", help="下载目录，默认 ./downloads")
    ap.add_argument("--filter", default="", help="按包名过滤，如 x64 / arm64 / x86")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    ap.add_argument(
        "--device-token",
        default="",
        help="覆盖内置的匿名设备票据（也可用环境变量 MSSTORE_DEVICE_TOKEN）",
    )
    args = ap.parse_args(argv)

    global DEVICE_TOKEN
    override = (args.device_token or os.environ.get("MSSTORE_DEVICE_TOKEN") or "").strip()
    if override:
        DEVICE_TOKEN = override

    pid = args.product_id.rstrip("/").split("/")[-1].split("?")[0]
    log = (lambda *a: None) if args.json else print

    log("[1/4] 获取匿名票据 ...")
    cookie, expiry = get_cookie()

    log("[2/4] 查询产品信息 ...")
    info = get_product(pid, args.market, args.locale)
    if not info["category_id"]:
        raise RuntimeError("未取到 WuCategoryId，该产品可能不是 appx/msix 打包应用")
    log("      %s / %s" % (info["title"], info["publisher"]))

    log("[3/4] 拉取包清单 ...")
    packages = sync_updates(cookie, expiry, info["category_id"], args.ring)
    if args.filter:
        kw = args.filter.lower()
        packages = [p for p in packages if kw in p["name"].lower()]
    if not packages:
        raise RuntimeError("没有匹配的包，可去掉 --filter 或换个 --ring 试试")

    log("[4/4] 换取下载直链 ...")
    for p in packages:
        p["url"] = get_url(p["update_id"], p["revision"], args.ring, p["digest"])

    if args.download:
        os.makedirs(args.out, exist_ok=True)
        for p in packages:
            dest = os.path.join(args.out, p["name"])
            log("      下载 %s (%s) ..." % (p["name"], human(p["size"])))
            download(p["url"], dest, p["size"], p["digest"])
            p["saved_to"] = dest

    if args.json:
        print(json.dumps({"product": info, "packages": packages}, ensure_ascii=False, indent=2))
    else:
        print()
        for p in packages:
            print("  %s" % p["name"])
            print("    大小: %s" % human(p["size"]))
            print("    直链: %s" % p["url"])
            if p.get("saved_to"):
                print("    已存: %s" % p["saved_to"])
            print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("错误: %s" % e, file=sys.stderr)
        sys.exit(1)
