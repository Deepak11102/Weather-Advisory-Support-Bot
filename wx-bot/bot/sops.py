import operator, os, pathlib, yaml
ROOT = pathlib.Path(__file__).resolve().parent.parent
OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq}
SEV = {"critical": 4, "high": 3, "moderate": 2, "low": 1, "info": 0}

def fields(node):
    if "field" in node: yield node["field"]
    for k in ("all", "any"):
        for n in node.get(k, []): yield from fields(n)

def _check(node):
    if "field" in node:
        assert node["op"] in OPS, f"bad op {node['op']}"
    elif not ("all" in node or "any" in node): raise ValueError(f"bad condition {node}")
    for k in ("all", "any"):
        for n in node.get(k, []): _check(n)

def load(path=None):
    cat = yaml.safe_load(pathlib.Path(path or os.getenv("SOP_FILE", ROOT / "sops" / "sops.yaml")).read_text())
    ids = set()
    for s in cat["sops"]:
        assert s["id"] not in ids, f"duplicate id {s['id']}"; ids.add(s["id"])
        assert s["severity"] in SEV, f"{s['id']}: bad severity"
        assert all(t == "*" or t in cat["tags"] for t in s["tags"]), f"{s['id']}: unknown tag"
        _check(s["when"])
    return cat

def required_vars(cat):
    """Weather variables to request = whatever the SOPs reference (so a new SOP needs no fetch-code change)."""
    return sorted({f.split(".")[0] for s in cat["sops"] for f in fields(s["when"])})

def ev(node, facts):
    if "all" in node: return all(ev(n, facts) for n in node["all"])
    if "any" in node: return any(ev(n, facts) for n in node["any"])
    v = facts.get(node["field"])
    return v is not None and OPS[node["op"]](v, node["value"])   # missing data never counts as 'safe'

def match(cat, tags, in_scope, facts):
    out = []
    for s in cat["sops"]:
        applies = (in_scope and "*" in s["tags"]) or bool(set(s["tags"]) & set(tags))
        if applies and ev(s["when"], facts): out.append(s)
    return out

def resolve(matched):
    m = sorted(matched, key=lambda s: (not s.get("lead", False), -SEV[s["severity"]]))
    if any(s["severity"] != "info" for s in m): m = [s for s in m if s["severity"] != "info"]
    return m[:3]