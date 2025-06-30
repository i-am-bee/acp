import json
import toml
import sys
import os

# Read package.json
with open("typescript/package.json", "r") as f:
    package_json = json.load(f)
    js_version = package_json.get("version")

# Read pyproject.toml
with open("python/pyproject.toml", "r") as f:
    pyproject = toml.load(f)
    py_version = pyproject.get("project", {}).get("version")

# Get version from github.ref if it's a tag
ref_version = None
github_ref = os.getenv("GITHUB_REF", "")
if github_ref.startswith("refs/tags/v"):
    ref_version = github_ref.replace("refs/tags/v", "")

# Compare versions
versions = [v for v in [js_version, py_version, ref_version] if v]
if len(versions) < 3:
    print("Error: Could not find version in files or tag")
    sys.exit(1)

if len(set(versions)) == 1:
    print(f"Versions match: {versions[0]}")
    sys.exit(0)
else:
    print("Version mismatch detected:")
    print(f"package.json: {js_version}")
    print(f"pyproject.toml: {py_version}")
    print(f"git tag: {ref_version}")
    sys.exit(1)
