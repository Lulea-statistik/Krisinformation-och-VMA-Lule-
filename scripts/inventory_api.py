#!/usr/bin/env python3
"""API v3 history discovery. Every result is an unverified candidate."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

API="https://api.krisinformation.se/v3/news"
OUT=Path("data/api_candidates.json")
KEYWORDS=("luleå","lulea","ytterviken","storheden","gammelstad","sunderbyn","hertsön","porsön","råneå","norrbotten")
VMA=("vma","viktigt meddelande till allmänheten","faran över")

def main():
    days=int(os.getenv("HISTORY_DAYS","7300"))
    number=int(os.getenv("HISTORY_COUNT","5000"))
    variants=[
      {"format":"json","allcounties":"true","days":days},
      {"format":"json","allcounties":"true","numberOfNewsArticles":number}
    ]
    attempts=[]; items={}; received=0
    for params in variants:
        url=API+"?"+urlencode(params)
        try:
            with urlopen(Request(url,headers={"User-Agent":"Lulea-VMA-history/1.1","Accept":"application/json"}),timeout=90) as resp:
                payload=json.load(resp)
            if isinstance(payload,list): articles=payload
            elif isinstance(payload,dict):
                articles=next((payload[k] for k in ("Items","items","News","news","Results","results") if isinstance(payload.get(k),list)),[])
            else: articles=[]
            received+=len(articles)
            attempts.append({"request":params,"ok":True,"article_count":len(articles)})
            for a in articles:
                if not isinstance(a,dict): continue
                blob=" ".join(str(a.get(k,"")) for k in ("Headline","Preamble","BodyText","Area","Web","headline","preamble","bodyText","area","web"))
                lower=blob.casefold()
                if not any(k in lower for k in KEYWORDS):continue
                link=a.get("Web") or a.get("web") or ""
                ident=str(a.get("Id") or a.get("id") or link or a.get("Headline") or a.get("headline"))
                if not ident:continue
                items[ident]={
                    "source_id":ident,
                    "headline":a.get("Headline") or a.get("headline"),
                    "published":a.get("Published") or a.get("published"),
                    "url":link,
                    "area":a.get("Area") or a.get("area"),
                    "possible_vma":any(k in lower for k in VMA),
                    "review_status":"unverified_candidate",
                    "geography_review":"needed",
                    "source":"Krisinformation API v3"
                }
        except Exception as exc:
            attempts.append({"request":params,"ok":False,"error":str(exc)[:300]})
    result={"generated_utc":datetime.now(timezone.utc).isoformat(),
      "notice":"Candidate search only. API response may be capped, filtered or incomplete. No entries are automatically verified as formal VMA.",
      "attempts":attempts,"total_articles_returned_across_queries":received,
      "candidates":sorted(items.values(),key=lambda a:str(a.get("published") or ""),reverse=True)}
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    print("Results:",json.dumps({"attempts":attempts,"candidates":len(items)},ensure_ascii=False))
    if not any(a["ok"] for a in attempts):
        raise SystemExit("Both API requests failed: see attempts in data/api_candidates.json")
if __name__=="__main__":main()
