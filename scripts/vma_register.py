"""In-memory VMA incident register. Synthetic/testing only until reuse terms verified."""
from datetime import datetime, timezone
from scripts.vma_incidents import group_messages
from scripts.sr_vma_pilot import matched_municipalities, MUNICIPALITIES

def parsed_time(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        t=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except ValueError:
        return None

def incident_record(messages, now=None):
    now=now or datetime.now(timezone.utc)
    actual=[m for m in messages if isinstance(m,dict) and m.get("status")=="Actual"]
    if not actual:
        return {"state":"excluded_non_actual","municipalities":[],"message_count":0}
    ordered=sorted(actual,key=lambda m: parsed_time(m.get("sent")) or datetime.min.replace(tzinfo=timezone.utc))
    first,last=ordered[0],ordered[-1]
    counts={}
    codes=set()
    for m in ordered:
        kind=m.get("msgType")
        counts[kind]=counts.get(kind,0)+1
        codes.update(matched_municipalities(m))
    # A Cancel may carry the sole geographic assignment; do not infer it as active.
    for m in ordered:
        if m.get("msgType")=="Cancel":
            for info in m.get("info") or []:
                if not isinstance(info,dict):continue
                for area in info.get("area") or []:
                    if not isinstance(area,dict):continue
                    for geo in area.get("geocode") or []:
                        if isinstance(geo,dict) and geo.get("valueName")=="Kommun" and str(geo.get("value")) in MUNICIPALITIES:
                            codes.add(str(geo["value"]))
    last_type=last.get("msgType")
    expires=[]
    for info in last.get("info") or []:
        if isinstance(info,dict):
            expires.append(parsed_time(info.get("expires")))
    if last_type=="Cancel":
        state="cancelled"
    elif last_type not in ("Alert","Update"):
        state="unknown"
    elif not expires or any(x is None for x in expires):
        state="unverified_expiration"
    elif all(x<=now for x in expires):
        state="expired"
    else:
        state="potentially_active_not_verified"
    return {"state":state,"municipalities":[{"code":c,"name":MUNICIPALITIES[c]} for c in sorted(codes)],
            "message_count":len(ordered),"update_count":counts.get("Update",0),
            "first_sent":first.get("sent"),"last_sent":last.get("sent"),
            "warning":"Potentially active is not an official live confirmation."}

def build_register(alerts,now=None):
    return [incident_record(m,now) for m in group_messages(alerts).values()]
