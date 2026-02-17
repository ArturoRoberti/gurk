from .common import PACKAGE_CACHE_PATH

GIT_MIRRORS_DIR = PACKAGE_CACHE_PATH / "git_mirrors"
GIT_MIRRORS_DIR.mkdir(parents=True, exist_ok=True)

PACKAGE_GIT_CACHE_METADATA_PATH = GIT_MIRRORS_DIR / "registry.yaml"
PACKAGE_GIT_CACHE_METADATA_PATH.touch(exist_ok=True)

GIT_QUERY_VERSIONING_FIELDS = {"branch", "commit", "version"}
