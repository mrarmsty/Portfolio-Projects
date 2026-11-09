"""Validates every PBIR JSON file against the Microsoft schema it declares (local clone of microsoft/json-schemas)."""
import json, sys
from pathlib import Path
from jsonschema import Draft7Validator
from referencing import Registry, Resource
SCHEMAS = Path(sys.argv[1])          # path to json-schemas/fabric
BASE = "https://developer.microsoft.com/json-schemas/fabric/"
def retrieve(uri):
    rel = uri.replace(BASE, "")
    return Resource.from_contents(json.loads((SCHEMAS / rel).read_text(encoding="utf-8")))
registry = Registry(retrieve=retrieve)
errors = 0; n = 0
for f in Path(sys.argv[2]).rglob("*.json"):
    doc = json.loads(f.read_text(encoding="utf-8"))
    sid = doc.get("$schema")
    if not sid: continue
    n += 1
    schema = json.loads((SCHEMAS / sid.replace(BASE, "")).read_text(encoding="utf-8"))
    v = Draft7Validator(schema, registry=registry)
    for e in v.iter_errors(doc):
        errors += 1
        print(f.relative_to(sys.argv[2]), "|", list(e.absolute_path)[:8], "|", e.message[:300])
print(f"validated {n} files, {errors} errors")
