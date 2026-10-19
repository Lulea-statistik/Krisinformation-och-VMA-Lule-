#!/usr/bin/env python3
"""Discover historical candidate URLs via official sitemap(s); never assert completeness."""
import gzip, json, re, time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse, urljoin

ROOT = "https://www.krisinformation.se"
OUTPUT = Path("data/sitemap_candidates.json")
MAX_SITEMAPS = 150
MAX_URLS = 150000
LOCAL = ("lulea", "luleå", "ytterviken", "storheden", "gammelstad", "sunderbyn", "hertson", "hertsön", "ranea", "råneå", "porson", "porsön")
REGIONAL = ("norrbotten", "boden", "pitea", "piteå", "kalix", "alvsbyn", "älvsbyn", "arvidsjaur", "kiruna", "gallivare", "gällivare")
VMA = ("vma", "viktigt-meddelande", "viktigt_meddelande")
def retrieve(url):
    req=Request(url, headers={"User-Agent":"Lulea-history-sitemap-inventory/1.0", "Accept":"application/xml,text/xml,text/plain,*/*"})
    with urlopen(req,timeout=35) as resp:
        content=resp.read(15_000_000)
    return gzip.decompress(content) if content[:2] == b"\x1f\x8b" else content

def main():
    checked=[]; queue=[]; seen=set(); urls=set(); errors=[]
    try:
        robots=retrieve(ROOT+"/robots.txt").decode("utf-8","replace")
        queue=[urljoin(ROOT, m.group(1).strip()) for m in re.finditer(r"(?im)^sitemap:\s*(\S+)",robots)]
    except Exception as exc:
        errors.append({"url": ROOT+"/robots.txt","error":str(exc)[:180]})
    queue.extend([ROOT+"/sitemap.xml",ROOT+"/sitemap_index.xml"])
    while queue and len(seen)<MAX_SITEMAPS and len(urls)<MAX_URLS:
        url=queue.pop(0)
        if url in seen or urlparse(url).hostname not in ("krisinformation.se","www.krisinformation.se"):continue
        seen.add(url)
        try:
            raw=retrieve(url)
            try:
                root=ET.fromstring(raw)
            except (ET.ParseError, ValueError) as first_error:
                # Some legacy sitemap servers declare an incorrect XML encoding.
                # Retry a Unicode parse only after removing the incorrect declaration.
                decoded=None
                for codec in ("utf-8-sig", "windows-1252"):
                    try:
                        decoded=raw.decode(codec)
                        break
                    except UnicodeDecodeError:
                        pass
                if decoded is None:
                    raise first_error
                decoded=re.sub(r'^\\s*<\\?xml[^>]*\\?>', '', decoded, count=1)
                root=ET.fromstring(decoded)
            tag=root.tag.rsplit("}",1)[-1].lower()
            locations=[(x.text or "").strip() for x in root.iter() if x.tag.rsplit("}",1)[-1].lower()=="loc"]
            if tag=="sitemapindex":
                queue.extend(loc for loc in locations if loc not in seen)
            elif tag=="urlset":
                urls.update(loc for loc in locations if urlparse(loc).hostname in ("krisinformation.se","www.krisinformation.se"))
            checked.append({"url":url,"ok":True,"type":tag,"locations":len(locations)})
        except Exception as exc:
            checked.append({"url":url,"ok":False,"error":str(exc)[:220]})
        time.sleep(.15)
    candidates=[]
    for url in sorted(urls):
        path=urlparse(url).path.casefold()
        if not any(s in path for s in LOCAL+REGIONAL+VMA):continue
        if not any(s in path for s in ("/nyheter/","/aktuellt/","/news/")):continue
        group="lulea_url" if any(s in path for s in LOCAL) else ("regional_url" if any(s in path for s in REGIONAL) else "generic_vma_url")
        candidates.append({"url":url,"candidate_class":group,"review_status":"unverified_candidate","source":"official_sitemap"})
    OUTPUT.parent.mkdir(exist_ok=True,parents=True)
    result={"generated_utc":datetime.now(timezone.utc).isoformat(),"status":"discovery_only",
            "warning":"Sitemaps may omit historical pages. Candidate URLs do not establish a formal VMA or Lulea relevance.",
            "sitemap_checks":checked,"errors":errors,"urls_discovered":len(urls),
            "queue_remaining":len(queue),"sitemap_limit_reached":len(seen)>=MAX_SITEMAPS,
            "url_limit_reached":len(urls)>=MAX_URLS,"candidate_count":len(candidates),"candidates":candidates}
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("urls_discovered","candidate_count","queue_remaining","sitemap_limit_reached","url_limit_reached")},ensure_ascii=False))
    if not any(x.get("ok") for x in checked):
        raise SystemExit("No accessible XML sitemap; diagnostics were saved")
if __name__=="__main__": main()
