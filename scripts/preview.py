"""Serve the portal and static assets on separate loopback ports."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from shutil import copyfile
from threading import Thread

from build import DIST, ROOT, build


class AssetHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def prepare(target, assets):
    target.mkdir(exist_ok=True, parents=True)
    for name in ("index.html", "blog-widget.html"):
        source = (ROOT / "portal" / name).read_text(encoding="utf-8")
        (target / name).write_text(source.replace("__ASSETS__", assets.rstrip("/")), encoding="utf-8")
    copyfile(ROOT / "portal/logo.png", target / "logo.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-url", help="Generate installation files for this HTTPS asset origin and exit")
    args = parser.parse_args()
    build()
    if args.assets_url:
        if not args.assets_url.startswith("https://"):
            parser.error("--assets-url requires an HTTPS URL")
        prepare(ROOT / ".preview/install", args.assets_url)
    else:
        target = ROOT / ".preview/portal"
        prepare(target, "http://127.0.0.1:8766")
        widget = (target / "blog-widget.html").read_text(encoding="utf-8")
        (target / "blog.html").write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>記事下プレビュー</title>' + widget + "</html>", encoding="utf-8")
        with ThreadingHTTPServer(("127.0.0.1", 8766), partial(AssetHandler, directory=DIST)) as assets, ThreadingHTTPServer(("127.0.0.1", 8765), partial(SimpleHTTPRequestHandler, directory=target)) as portal:
            Thread(target=assets.serve_forever, daemon=True).start()
            print("Portal: http://127.0.0.1:8765/   Blog: http://127.0.0.1:8765/blog.html", flush=True)
            portal.serve_forever()
