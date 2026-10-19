"""CAP VMA incident grouping, for verified internal modeling only.

Never persist real identifiers or CAP content without source permission.
"""
from collections import defaultdict

def incident_key(alert):
    """Group by declared CAP incidents, else by reference chain, else message ID."""
    if not isinstance(alert, dict):
        return None
    incidents = alert.get("incidents")
    if isinstance(incidents, str) and incidents.strip():
        return ("incident", incidents.strip())
    if isinstance(incidents, list) and incidents:
        values = tuple(sorted(str(x).strip() for x in incidents if x))
        if values:
            return ("incident", values)
    references = alert.get("references")
    if isinstance(references, str) and references.strip():
        first = references.strip().split()[0].split(",")
        if len(first) >= 2:
            return ("reference", first[1].strip())
    identifier = alert.get("identifier")
    return ("message", str(identifier)) if identifier else None

def group_messages(alerts):
    """Group messages by declared key; do not infer from timing/place."""
    groups = defaultdict(list)
    for alert in alerts:
        key = incident_key(alert)
        if key is not None:
            groups[key].append(alert)
    return groups

def classify_group(messages):
    """Conservative snapshot classification; Cancel supersedes earlier alerts."""
    ordered = sorted(messages, key=lambda x: str(x.get("sent") or ""))
    latest = ordered[-1]
    kind = latest.get("msgType")
    if latest.get("status") != "Actual":
        return "not_actual"
    if kind == "Cancel":
        return "cancelled"
    if kind in ("Alert", "Update"):
        return "potentially_active"
    return "unknown"
