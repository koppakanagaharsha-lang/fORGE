#!/usr/bin/env python3
"""
FORGE Phantom — Chrome DevTools Protocol Client
Domain allowlist enforced on every navigation.
FORGE's eyes and hands on the web.
"""

import sys, json, time, base64, urllib.request
from urllib.parse import urlparse

ALLOWED_DOMAINS = [
    "github.com", "api.github.com", "raw.githubusercontent.com",
    "gist.github.com", "clawhub.dev", "api.clawhub.dev",
    "news.ycombinator.com", "npmjs.com", "registry.npmjs.org",
    "pypi.org", "docs.python.org", "developer.mozilla.org",
    "stackoverflow.com", "arxiv.org",
    "aistudio.google.com", "accounts.google.com",
    "opencode.ai", "docs.anthropic.com",
]

def is_allowed(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False

try:
    import websocket
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install",
                    "websocket-client", "--break-system-packages", "-q"],
                   capture_output=True)
    import websocket

def get_ws():
    try:
        with urllib.request.urlopen("http://localhost:9222/json", timeout=5) as r:
            tabs = json.loads(r.read())
        for t in tabs:
            if t.get("type") == "page":
                return t["webSocketDebuggerUrl"]
        urllib.request.urlopen("http://localhost:9222/json/new", timeout=5)
        return get_ws()
    except Exception as e:
        print(f"Phantom offline: {e}", file=sys.stderr)
        sys.exit(1)

class Phantom:
    def __init__(self):
        self.ws = websocket.create_connection(get_ws(), timeout=30)
        self._id = 0

    def _send(self, method, params=None):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method,
                                  "params": params or {}}))
        while True:
            d = json.loads(self.ws.recv())
            if d.get("id") == self._id:
                if "error" in d:
                    raise RuntimeError(f"CDP: {d['error']}")
                return d.get("result", {})

    def navigate(self, url: str) -> None:
        if not is_allowed(url):
            raise PermissionError(
                f"Blocked: {urlparse(url).netloc} — not on FORGE allowlist"
            )
        self._send("Page.enable")
        self._send("Page.navigate", {"url": url})
        deadline = time.time() + 20
        while time.time() < deadline:
            r = self._send("Runtime.evaluate",
                           {"expression": "document.readyState"})
            if r.get("result", {}).get("value") == "complete":
                break
            time.sleep(0.4)

    def text(self) -> str:
        r = self._send("Runtime.evaluate", {"expression": """(function() {
            var c = document.cloneNode(true);
            c.querySelectorAll('script,style,nav,footer,header,[aria-hidden]')
             .forEach(e => e.remove());
            return (c.body ? c.body.innerText : '')
              .split('\\n').map(l => l.trim()).filter(Boolean).join('\\n');
        })()"""})
        return r.get("result", {}).get("value", "")

    def links(self) -> list:
        r = self._send("Runtime.evaluate", {
            "expression": """Array.from(document.querySelectorAll('a[href]'))
              .map(a => ({text: a.innerText.trim().slice(0,80), url: a.href}))
              .filter(l => l.text && l.url.startsWith('http'))
              .slice(0, 60)""",
            "returnByValue": True
        })
        return r.get("result", {}).get("value", [])

    def screenshot(self, path: str) -> str:
        r = self._send("Page.captureScreenshot", {"format": "png"})
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path

    def ev(self, js: str):
        return self._send("Runtime.evaluate",
                          {"expression": js}).get("result", {}).get("value")

    def click(self, sel: str) -> str:
        return self.ev(f"""(()=>{{
            var e=document.querySelector({json.dumps(sel)});
            if(!e) return 'not found: {sel}';
            e.click(); return 'clicked';
        }})()""")

    def fill(self, sel: str, val: str) -> str:
        return self.ev(f"""(()=>{{
            var e=document.querySelector({json.dumps(sel)});
            if(!e) return 'not found: {sel}';
            e.focus(); e.value={json.dumps(val)};
            e.dispatchEvent(new Event('input',{{bubbles:true}}));
            e.dispatchEvent(new Event('change',{{bubbles:true}}));
            return 'filled';
        }})()""")

    def wait(self, sel: str, timeout: int = 10) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.ev(f"!!document.querySelector({json.dumps(sel)})"):
                return True
            time.sleep(0.4)
        return False

    def scroll(self, direction: str = "bottom") -> None:
        self.ev("window.scrollTo(0,document.body.scrollHeight)"
                if direction == "bottom" else "window.scrollTo(0,0)")
        time.sleep(0.3)

    def close(self):
        self.ws.close()

def main():
    if len(sys.argv) < 2:
        print("FORGE Phantom\nUsage: cdp.py <command> [args]")
        sys.exit(0)

    cmd, args = sys.argv[1], sys.argv[2:]

    if cmd == "allowed":
        u = args[0] if args else ""
        print("allowed" if is_allowed(u) else f"blocked: {urlparse(u).netloc}")
        return

    p = Phantom()
    try:
        if cmd == "navigate":
            p.navigate(args[0])
            print(f"url: {p.ev('location.href')}")
            print(f"title: {p.ev('document.title')}")
        elif cmd == "text":      print(p.text())
        elif cmd == "links":
            for l in p.links():
                print(f"{l['text'][:60]:<60}  {l['url']}")
        elif cmd == "screenshot":
            path = args[0] if args else "/tmp/forge-shot.png"
            print(p.screenshot(path))
        elif cmd == "click":     print(p.click(args[0]))
        elif cmd == "fill":      print(p.fill(args[0], args[1]))
        elif cmd == "eval":      print(p.ev(args[0]))
        elif cmd == "wait":
            t = int(args[1]) if len(args) > 1 else 10
            print("found" if p.wait(args[0], t) else "timeout")
        elif cmd == "scroll":    p.scroll(args[0] if args else "bottom"); print("ok")
        elif cmd == "title":     print(p.ev("document.title"))
        elif cmd == "url":       print(p.ev("location.href"))
        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            sys.exit(1)
    except PermissionError as e:
        print(f"PHANTOM BLOCKED: {e}", file=sys.stderr)
        sys.exit(2)
    finally:
        p.close()

if __name__ == "__main__":
    main()
