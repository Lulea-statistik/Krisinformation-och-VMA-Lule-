#!/usr/bin/env python3
"""Inventory candidate Lulea crisis articles from public year archive pages.

Candidate links are NOT confirmed incidents and must not be displayed as verified VMA.
"""
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE = "https://www.krisinformation.se"
START_YEAR = 2010
END_YEAR = datetime.now(timezone.utc).year
KEYWORDS = ("luleå", "lulea", "norrbotten", "storheden", "ytterviken", "gammelstad",
            "sunderbyn", "porsön", "hertsön", "råneå", "södra sunderbyn")
VMA_TERMS = ("vma", "viktigt meddelande", "faran över")
OUT = Path("data/archive_candidates.json")

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.texts = []
        self.results = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.texts = []
    def handle_data(self, data):
        if self.href is not None:
            self.texts.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.results.append((self.href, " ".join(" ".join(self.texts).split())))
            self.href = None

def fetch(url):
    req = Request(url, headers={"User-Agent": "Lulea-VMA-history-research/1.0 (+https://github.com/Lulea-statistik/Krisinformation-och-VMA-Lule-)"})
    with urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")

def main():
    results = {}
    coverage = []
    for year in range(START_YEAR, END_YEAR + 1):
        url = f"{BASE}/nyheter/{year}/"
        try:
            parser = Links()
            parser.feed(fetch(url))
            hits = 0
            for href, title in parser.results:
                target = urljoin(url, href)
                path = urlparse(target).path
                if urlparse(target).hostname not in ("www.krisinformation.se", "krisinformation.se"):
                    continue
                if not re.search(r"/nyheter/(?:19|20)\d{2}/", path):
                    continue
                if path.rstrip("/") == f"/nyheter/{year}":
                    continue
                haystack = (title + " " + path).casefold()
                if not any(term in haystack for term in KEYWORDS):
                    continue
                key = target.rstrip("/").split("?")[0]
                results[key] = {"url": key, "archive_year": year, "archive_title": title,
                                "possible_vma": any(term in haystack for term in VMA_TERMS),
                                "review_status": "unverified_candidate"}
                hits += 1
            coverage.append({"year": year, "archive_accessible": True, "matching_links": hits})
            print(year, hits)
        except Exception as error:
            coverage.append({"year": year, "archive_accessible": False, "error": str(error)[:160]})
            print(year, type(error).__name__, str(error)[:100])
        time.sleep(0.4)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "disclaimer": "Search candidates only: NOT verified VMA or complete archive coverage.",
               "coverage": coverage, "candidates": sorted(results.values(), key=lambda x:(x["archive_year"], x["url"]))}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Candidates:", len(results))
if __name__ == "__main__":
    main()
