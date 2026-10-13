#!/usr/bin/env python3
"""Tell IndexNow (Bing, Yandex, Seznam, Naver, Yep) which pages really changed — run after the deploy.

    CHANGED="https://… https://…" python3 indexnow.py

The list comes from build.py (pages whose content differs from the live site, dates aside). The key file
/<INDEXNOW_KEY>.txt is published with the site. Nothing changed → nothing is sent.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

from build import BASE, INDEXNOW_KEY

HOST = BASE.split("//", 1)[1]


def main() -> int:
    urls = [u for u in os.environ.get("CHANGED", "").split() if u.startswith(BASE)]
    if not urls:
        print("IndexNow: nothing changed.")
        return 0
    body = json.dumps({"host": HOST, "key": INDEXNOW_KEY, "keyLocation": f"{BASE}/{INDEXNOW_KEY}.txt",
                       "urlList": urls[:10000]}).encode()
    for attempt in range(3):
        request = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                         headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                print(f"IndexNow: {len(urls)} page(s) reported, HTTP {response.status}.")
                return 0
        except urllib.error.HTTPError as error:
            # 403: the key file is not live yet (first deploy) — try again a little later.
            print(f"IndexNow: HTTP {error.code} {error.read()[:200]!r}")
            if error.code not in (403, 429, 500, 502, 503):
                return 0          # a refusal is not worth failing the deploy for
        except OSError as error:
            print(f"IndexNow: {error}")
        time.sleep(30 * (attempt + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
