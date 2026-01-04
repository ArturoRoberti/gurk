import requests
import toml
from packaging.version import InvalidVersion, Version

# Check internet connection
try:
    requests.get("https://pypi.org", timeout=5)
except requests.RequestException:
    # No internet connection, skip version bump
    exit(0)

# Load local version
data = toml.load("pyproject.toml")
local_ver = Version(data["project"]["version"])

# Load PyPI versions
pypi_versions = []
resp = requests.get(
    "https://pypi.org/pypi/gurk/json",
    timeout=10,
    headers={"Accept-Encoding": "*"},
)
if resp.status_code == 200 and resp.headers.get("content-type", "").startswith(
    "application/json"
):
    payload = resp.json()
    for v in payload.get("releases", {}):
        try:
            pypi_versions.append(Version(v))
        except InvalidVersion:
            pass

# Determine new version
if pypi_versions:
    highest = max(pypi_versions)
    if local_ver <= highest:
        new_version = Version(
            f"{highest.major}.{highest.minor}.{highest.micro + 1}"
        )
    else:
        new_version = local_ver
else:
    new_version = local_ver

# Write back
data["project"]["version"] = str(new_version)
with open("pyproject.toml", "w") as f:
    toml.dump(data, f)
