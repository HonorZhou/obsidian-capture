#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Playwright 自带 Chromium 引导抖音真 cookie，写成 Netscape cookies.txt。

背景：抖音 web API 要求真实浏览器执行过 JS 才产生的 cookie（__ac_signature /
msToken / webid 等），仅靠 ttwid 注册接口会被 yt-dlp 判为
"Fresh cookies (not necessarily logged in) are needed"。

关键设计：**不读系统浏览器**（Edge/Chrome 运行时会独占锁定 cookie 库，
读它还会干扰用户正在用的窗口）。本脚本用 Playwright 自带的独立 Chromium
与独立临时 profile，与用户浏览器完全隔离。

用法：
    python dy_cookie.py [输出 cookies.txt 路径] [--url 视频页]

环境变量：
    DY_COOKIE_OUT   输出路径，默认 D:/tools/cookies.txt
    PW_BROWSERS     若设置，则同时写入 PLAYWRIGHT_BROWSERS_PATH
    DY_HEADFUL=1    显示浏览器窗口（调试用）
"""
import argparse
import os
import sys
from pathlib import Path

if os.environ.get("PW_BROWSERS"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.environ["PW_BROWSERS"]

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("[dy_cookie] 需要 playwright：pip install playwright && python -m playwright install chromium")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

HOME = "https://www.douyin.com/"
# yt-dlp 的 Douyin 提取器要用 msToken + webid 现算 a_bogus 签名；
# 只有 __ac_signature/ttwid 会被判为 "Fresh cookies (not necessarily logged in) are needed"。
MUST_HAVE = {"msToken", "webid"}
# 这些是抖音反爬真正看的 cookie，拿到任意一个即说明 JS 指纹已生成
WANTED = MUST_HAVE | {"__ac_nonce", "__ac_signature", "ttwid",
                      "UIFID", "UIFID_TEMP", "passport_csrf_token", "s_v_web_id"}


def to_netscape(cookies: list) -> str:
    lines = ["# Netscape HTTP Cookie File", "# dy_cookie.py generated", ""]
    for c in cookies:
        name = c.get("name")
        value = c.get("value")
        domain = c.get("domain") or ""
        if not name or value is None:
            continue
        path = c.get("path") or "/"
        secure = "TRUE" if c.get("secure") else "FALSE"
        exp = c.get("expires") or -1
        exp_s = "0" if (exp is None or exp < 0) else str(int(exp))
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        lines.append("\t".join([domain, flag, path, secure, exp_s, name, value]))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="引导抖音真 cookie -> cookies.txt")
    ap.add_argument("out", nargs="?", default=os.environ.get("DY_COOKIE_OUT", "D:/tools/cookies.txt"))
    ap.add_argument("--url", default=HOME, help="额外访问的页面（如具体视频页），触发签名接口")
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("DY_COOKIE_TIMEOUT", "60")),
                    help="等待必备 cookie(msToken/webid) 出现的总超时秒数")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headless = not os.environ.get("DY_HEADFUL")
    all_cookies = {}

    def harvest(ctx):
        for c in ctx.cookies():
            all_cookies[(c.get("domain"), c.get("name"))] = c

    def have():
        return {k[1] for k in all_cookies}

    with sync_playwright() as p:
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run", "--no-default-browser-check",
            "--lang=zh-CN",
            "--window-size=1366,768",
        ]
        # 持久化 profile：抖音对同一 profile 的第二次访问信任度更高
        udd = os.environ.get("DY_COOKIE_UDD", "D:/tools/pw-profile")
        Path(udd).mkdir(parents=True, exist_ok=True)
        ctx = p.chromium.launch_persistent_context(
            udd, headless=headless, args=launch_args,
            user_agent=UA, locale="zh-CN", timezone_id="Asia/Shanghai",
            viewport={"width": 1366, "height": 768})
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh']});"
            "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});"
            "window.chrome={runtime:{},loadTimes:()=>{},csi:()=>{}};"
            "const q=navigator.permissions&&navigator.permissions.query;"
            "if(q){navigator.permissions.query=(p)=>q.call(navigator.permissions,p)"
            ".catch(()=>({state:'denied'}));}")
        browser = None
        page = ctx.new_page()

        # msToken 走响应头 x-ms-token，webid 走接口 JSON，二者都不再用 Set-Cookie 下发，
        # 因此必须拦响应再手动提升成 cookie。
        promoted = {}

        def on_response(resp):
            try:
                req_cookies = {}
                tok = resp.headers.get("x-ms-token")
                if tok:
                    req_cookies["msToken"] = tok
                u = resp.url or ""
                if ("webid" in u or "passport" in u or "risklevel" in u
                        or "account" in u or "get/user" in u):
                    try:
                        body = resp.json()
                    except Exception:  # noqa: BLE001
                        body = None
                    if isinstance(body, dict):
                        for src in (body, body.get("data") or {}):
                            if isinstance(src, dict):
                                wid = src.get("webid") or src.get("web_id")
                                if wid:
                                    req_cookies["webid"] = str(wid)
                                mst = src.get("msToken") or src.get("ms_token")
                                if mst:
                                    req_cookies.setdefault("msToken", str(mst))
                for name, val in req_cookies.items():
                    if promoted.get(name) == val:
                        continue
                    promoted[name] = val
                    ctx.add_cookies([{
                        "name": name, "value": val,
                        "domain": ".douyin.com", "path": "/",
                        "secure": True, "httpOnly": False, "sameSite": "None",
                    }])
                    print(f"[dy_cookie] 提升 cookie <- {name} ({resp.url[:70]})")
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)
        ctx.on("response", on_response)

        targets = [HOME, "https://www.douyin.com/discover"]
        if args.url and args.url not in targets:
            targets.append(args.url)

        deadline = args.timeout
        for t in targets:
            try:
                page.goto(t, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:  # noqa: BLE001
                print(f"[dy_cookie] 访问失败 {t}: {type(e).__name__} {str(e)[:150]}")
                continue
            # 轮询等待 msToken / webid（埋点 XHR 触发后才写入）
            waited = 0
            while waited < deadline:
                page.wait_for_timeout(1500)
                waited += 1.5
                harvest(ctx)
                if MUST_HAVE <= have():
                    break
            # 滚动一下，促使抖音前端加载更多内容并发签名请求
            try:
                page.mouse.wheel(0, 800)
                page.wait_for_timeout(1500)
            except Exception:  # noqa: BLE001
                pass
            harvest(ctx)
            if MUST_HAVE <= have():
                break

        got = have()
        missing = MUST_HAVE - got
        print(f"[dy_cookie] headless={headless} 采集 cookie 总数={len(all_cookies)}")
        print(f"[dy_cookie] 关键项={sorted(got & WANTED) or '无'}")
        if missing:
            print(f"[dy_cookie] !! 仍缺必备项 {sorted(missing)} —— "
                  f"无头模式可能被判自动化浏览器，试 DY_HEADFUL=1 有头重跑")

        ctx.close()

    cookie_list = list(all_cookies.values())
    out_path.write_text(to_netscape(cookie_list), encoding="utf-8", newline="")
    print(f"[dy_cookie] 已写出 {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
