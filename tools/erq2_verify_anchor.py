from __future__ import annotations
import argparse, hashlib, json, os, platform, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

EXPECTED = {
    "anchor": "cfcf7e968a5faf506fb6a59bf21d0e96d40b9601",
    "tree": "8e0488e3da3fb0f42b1092a8c541e984a813c877",
    "upstream": "08106b0c3771ef5b4a5aa176acccd460e88b7325",
    "upstream_tree": "d382e2a34200de59849132f78c1ee0123ffa8122",
    "license_blob": "28e6960dd9a2be209c308b49bc9a8973dbf4d60d",
    "tracked": 395,
    "manifest_id": "btdu-repo:1621b80b8100093c68d269dab2450e647aabb6cd5bd341cc7b6ef26a69620089",
    "aggregate": "056bb283803aade8aa0c0311660d53dd67469cf38864072a6709d3ffd2d3cf70",
    "atomic_root": "68214f419cf5cbe44eabb75bb850e9cb2d01bab8954600ad9da4f7f4fd306fff",
    "git_object_manifest": "2417c8bd4a39f369bd8ef36baa7184061c5a0e04374f2bb37aa485179c6f39ff",
    "governed_graph": "599baa14fcdf0961d072d97153ec347d5655a2386f3125e5f7c831027090cf27",
    "provenance": "9ad041653e1225b09414a09b779f894ed259d3ee26beedc985477499296315e2",
    "rights": "e5c09ce61741e181a5ff9ce351536101184a94af39b117d8e5dff838e853701e",
    "btg": "aaa91176db857e0ae4546746f4468850b96064d62b7d7faf90d86b81e2579534",
    "raw_ingest": "04f34098a067244338cbb4e176a9ff95573cb78653e2157088e158f70981926a",
}

def git(repo: Path, *args: str, binary: bool = False):
    cp = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=not binary)
    if cp.returncode != 0:
        err = cp.stderr.decode() if binary else cp.stderr
        raise SystemExit(err or f"git {' '.join(args)} failed")
    return cp.stdout

def req(name: str, actual, expected):
    if str(actual).lower() != str(expected).lower():
        raise SystemExit(f"{name}=FAIL expected={expected} actual={actual}")
    print(f"{name}=PASS")

def blob(repo: Path, path: str) -> bytes:
    return git(repo, "show", f"{EXPECTED['anchor']}:{path}", binary=True)

p = argparse.ArgumentParser()
p.add_argument("--repo", required=True)
args = p.parse_args()
repo = Path(args.repo)

req("ANCHOR", git(repo, "rev-parse", "HEAD").strip(), EXPECTED["anchor"])
req("TREE", git(repo, "rev-parse", "HEAD^{tree}").strip(), EXPECTED["tree"])
req("UPSTREAM", git(repo, "rev-parse", "HEAD^").strip(), EXPECTED["upstream"])
req("UPSTREAM_TREE", git(repo, "rev-parse", "HEAD^^{tree}").strip(), EXPECTED["upstream_tree"])
req("LICENSE_BLOB", git(repo, "rev-parse", f"{EXPECTED['upstream']}:LICENSE").strip(), EXPECTED["license_blob"])
req("TRACKED_PATHS", len([x for x in git(repo, "ls-tree", "-r", "--name-only", EXPECTED["upstream"]).splitlines() if x]), EXPECTED["tracked"])

pm = json.loads(blob(repo, ".entity/PUBLICATION_MANIFEST.json").decode("utf-8"))
for name, meta in pm["publication_files"].items():
    b = blob(repo, f".entity/{name}")
    req(f"BLOB_SHA256::{name}", hashlib.sha256(b).hexdigest(), meta["sha256"])
    req(f"BLOB_BYTES::{name}", len(b), meta["bytes"])

ing = json.loads(blob(repo, ".entity/ERQ1_BTDU_INGEST_PUBLIC.json").decode("utf-8"))
gov = json.loads(blob(repo, ".entity/ERQ1_GOVERNED_REPOSITORY.json").decode("utf-8"))
rights = json.loads(blob(repo, ".entity/ERQ1_RIGHTS_MANIFEST.json").decode("utf-8"))
btg = json.loads(blob(repo, ".entity/ERQ1_BTG_CONTRIBUTION.json").decode("utf-8"))

req("MANIFEST_ID", ing["manifest_id"], EXPECTED["manifest_id"])
req("AGGREGATE", ing["aggregate_sha256"], EXPECTED["aggregate"])
req("ATOMIC_ROOT", ing["atomic_root"], EXPECTED["atomic_root"])
req("RAW_INGEST_BINDING", ing["canonical_raw_manifest_sha256"], EXPECTED["raw_ingest"])
req("GIT_OBJECT_MANIFEST", gov["git_object_manifest_sha256"], EXPECTED["git_object_manifest"])
req("GOVERNED_GRAPH", gov["governed_object_graph_sha256"], EXPECTED["governed_graph"])
req("PROVENANCE", gov["provenance_graph_sha256"], EXPECTED["provenance"])
req("RIGHTS", gov["rights_manifest_sha256"], EXPECTED["rights"])
req("BTG_CONTRIBUTION", gov["btg_contribution_sha256"], EXPECTED["btg"])

if rights["btg_claims_upstream_source_ownership"] is not False:
    raise SystemExit("RIGHTS_BOUNDARY=FAIL")
if rights["ingestion_creates_ownership"] is not False:
    raise SystemExit("RIGHTS_BOUNDARY=FAIL")
if rights["ingestion_creates_economic_entitlement"] is not False:
    raise SystemExit("RIGHTS_BOUNDARY=FAIL")
if rights["upstream_rights_holder_entity_id"] is not None:
    raise SystemExit("RIGHTS_BOUNDARY=FAIL")
if btg["upstream_source_ownership_claimed"] is not False:
    raise SystemExit("RIGHTS_BOUNDARY=FAIL")
if btg["automatic_upstream_economic_entitlement_claimed"] is not False:
    raise SystemExit("RIGHTS_BOUNDARY=FAIL")
print("RIGHTS_BOUNDARY=PASS")

receipt = {
    "schema": "entity-erq2-platform-receipt-v1",
    "qualification": "ERQ-2 Cross-Platform Survival Qualification",
    "status": "PASS",
    "platform": {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_arch": os.environ.get("RUNNER_ARCH"),
    },
    "verified_utc": datetime.now(timezone.utc).isoformat(),
    "anchor_commit": EXPECTED["anchor"],
    "anchor_tree": EXPECTED["tree"],
    "upstream_commit": EXPECTED["upstream"],
    "upstream_tree": EXPECTED["upstream_tree"],
    "manifest_id": ing["manifest_id"],
    "aggregate_sha256": ing["aggregate_sha256"],
    "atomic_root": ing["atomic_root"],
    "provenance_sha256": gov["provenance_graph_sha256"],
    "rights_sha256": gov["rights_manifest_sha256"],
    "btg_contribution_sha256": gov["btg_contribution_sha256"],
    "rights_boundary_preserved": True,
    "canonical_git_blob_verification": True,
}
name = f"erq2-receipt-{platform.system().lower()}-{platform.machine().lower()}.json"
Path(name).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ERQ2_PLATFORM_VERIFY=PASS")
print(f"RECEIPT={name}")
