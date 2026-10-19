"""Conservative CAP incident grouping with identifier/reference chains.

This module processes records in memory only. Production archival permissions
must be verified separately. No inference from shared time or location.
"""
from collections import defaultdict

def _incident_tokens(alert):
    raw = alert.get("incidents")
    if isinstance(raw, str):
        return [s.strip() for s in raw.split(",") if s.strip()]
    if isinstance(raw, list):
        return [str(s).strip() for s in raw if str(s).strip()]
    return []

def _reference_ids(alert):
    raw = alert.get("references") or ""
    if not isinstance(raw, str):
        return []
    result = []
    for triple in raw.split():
        fields = triple.split(",")
        if len(fields) >= 3 and fields[1].strip():
            result.append(fields[1].strip())
    return result

def incident_key(alert):
    """A descriptive primary key, not the complete linked-incident identity."""
    if not isinstance(alert, dict):
        return None
    incidents = _incident_tokens(alert)
    if incidents:
        return ("incident", tuple(sorted(set(incidents))))
    identifier = str(alert.get("identifier") or "").strip()
    refs = _reference_ids(alert)
    if refs:
        return ("reference", refs[0])
    return ("message", identifier) if identifier else None

def group_messages(alerts):
    """Join explicit CAP incident tokens and known message reference chains.

    Reference edges must point to a message present in the supplied collection.
    Conflicting explicit incident identifiers remain separate for review.
    """
    records = [a for a in alerts if isinstance(a, dict)]
    parent = list(range(len(records)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def join(i,j):
        x,y=root(i),root(j)
        if x!=y:
            parent[y]=x
    by_identifier = {}
    by_incident = {}
    for i,a in enumerate(records):
        identifier=str(a.get("identifier") or "").strip()
        if identifier:
            by_identifier.setdefault(identifier, []).append(i)
        for token in _incident_tokens(a):
            if token in by_incident:
                join(i,by_incident[token])
            else:
                by_incident[token]=i
    for i,a in enumerate(records):
        for ref in _reference_ids(a):
            for j in by_identifier.get(ref,[]):
                left=set(_incident_tokens(a))
                right=set(_incident_tokens(records[j]))
                if left and right and left.isdisjoint(right):
                    continue
                join(i,j)
    groups=defaultdict(list)
    for i,a in enumerate(records):
        key=incident_key(a)
        if key is not None:
            groups[root(i)].append(a)
    return dict(groups)

def classify_group(messages):
    """Interpret last explicitly timestamped CAP message conservatively."""
    if not messages:
        return "unknown"
    ordered=sorted(messages,key=lambda a:str(a.get("sent") or ""))
    last=ordered[-1]
    if last.get("status")!="Actual":
        return "not_actual"
    if last.get("msgType")=="Cancel":
        return "cancelled"
    if last.get("msgType") in ("Alert","Update"):
        return "potentially_active"
    return "unknown"
