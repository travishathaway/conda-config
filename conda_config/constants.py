"""
Module that is used for declaring constant values for this library.

A lot of these values are copied over from the main conda project (conda.base.constants).
"""

import sys
import struct
from enum import Enum
from os.path import join

#: Name of the local channel
LOCAL_CHANNEL_NAME = "local"

ON_WIN = bool(sys.platform == "win32")

PREFIX_PLACEHOLDER = ("/opt/anaconda1anaconda2"
                      # this is intentionally split into parts, such that running
                      # this program on itself will leave it unchanged
                      "anaconda3")

MACHINE_BITS = 8 * struct.calcsize("P")

APP_NAME = "conda"

SEARCH_PATH: tuple[str, ...]

if ON_WIN:
    SEARCH_PATH = (
        "C:/ProgramData/conda/.condarc",
        "C:/ProgramData/conda/condarc",
        "C:/ProgramData/conda/condarc.d",
    )
else:
    SEARCH_PATH = (
        "/etc/conda/.condarc",
        "/etc/conda/condarc",
        "/etc/conda/condarc.d/",
        "/var/lib/conda/.condarc",
        "/var/lib/conda/condarc",
        "/var/lib/conda/condarc.d/",
    )

SEARCH_PATH += (
    "$CONDA_ROOT/.condarc",
    "$CONDA_ROOT/condarc",
    "$CONDA_ROOT/condarc.d/",
    "$XDG_CONFIG_HOME/conda/.condarc",
    "$XDG_CONFIG_HOME/conda/condarc",
    "$XDG_CONFIG_HOME/conda/condarc.d/",
    "~/.config/conda/.condarc",
    "~/.config/conda/condarc",
    "~/.config/conda/condarc.d/",
    "~/.conda/.condarc",
    "~/.conda/condarc",
    "~/.conda/condarc.d/",
    "~/.condarc",
    "$CONDA_PREFIX/.condarc",
    "$CONDA_PREFIX/condarc",
    "$CONDA_PREFIX/condarc.d/",
    "$CONDARC",
)

DEFAULT_CHANNEL_ALIAS = "https://conda.anaconda.org"
CONDA_HOMEPAGE_URL = "https://conda.io"
ERROR_UPLOAD_URL = "https://conda.io/conda-post/unexpected-error"
DEFAULTS_CHANNEL_NAME = "defaults"

KNOWN_SUBDIRS = PLATFORM_DIRECTORIES = (
    "noarch",
    "linux-32",
    "linux-64",
    "linux-aarch64",
    "linux-armv6l",
    "linux-armv7l",
    "linux-ppc64",
    "linux-ppc64le",
    "linux-s390x",
    "osx-64",
    "osx-arm64",
    "win-32",
    "win-64",
    "win-arm64",
    "zos-z",
)

RECOGNIZED_URL_SCHEMES = ("http", "https", "ftp", "s3", "file")


DEFAULT_CHANNELS_UNIX = (
    "https://repo.anaconda.com/pkgs/main",
    "https://repo.anaconda.com/pkgs/r",
)

DEFAULT_CHANNELS_WIN = (
    "https://repo.anaconda.com/pkgs/main",
    "https://repo.anaconda.com/pkgs/r",
    "https://repo.anaconda.com/pkgs/msys2",
)

DEFAULT_CUSTOM_CHANNELS = {
    "pkgs/pro": "https://repo.anaconda.com",
}

DEFAULT_CHANNELS = DEFAULT_CHANNELS_WIN if ON_WIN else DEFAULT_CHANNELS_UNIX

ROOT_ENV_NAME = "base"

ROOT_NO_RM = (
    "python",
    "pycosat",
    "ruamel.yaml",
    "conda",
    "openssl",
    "requests",
)

DEFAULT_AGGRESSIVE_UPDATE_PACKAGES = (
    "ca-certificates",
    "certifi",
    "openssl",
)

COMPATIBLE_SHELLS: tuple[str, ...]

if ON_WIN:
    COMPATIBLE_SHELLS = (
        "bash",
        "cmd.exe",
        "fish",
        "tcsh",
        "xonsh",
        "zsh",
        "powershell",
    )
else:
    COMPATIBLE_SHELLS = (
        "bash",
        "fish",
        "tcsh",
        "xonsh",
        "zsh",
        "powershell",
    )


# Maximum priority, reserved for packages we really want to remove
MAX_CHANNEL_PRIORITY = 10000

CONDA_PACKAGE_EXTENSION_V1 = ".tar.bz2"
CONDA_PACKAGE_EXTENSION_V2 = ".conda"
CONDA_PACKAGE_EXTENSIONS = (
    CONDA_PACKAGE_EXTENSION_V2,
    CONDA_PACKAGE_EXTENSION_V1,
)
CONDA_TARBALL_EXTENSION = CONDA_PACKAGE_EXTENSION_V1  # legacy support for conda-build; remove this line  # NOQA
CONDA_TEMP_EXTENSION = ".c~"
CONDA_TEMP_EXTENSIONS = (CONDA_TEMP_EXTENSION, ".trash")
CONDA_LOGS_DIR = ".logs"

UNKNOWN_CHANNEL = "<unknown>"
REPODATA_FN = "repodata.json"

#: Default name of the notices file on the server we look for
NOTICES_FN = "notices.json"

#: Name of cache file where read notice IDs are stored
NOTICES_CACHE_FN = "notices.cache"

#: Determines the subdir for notices cache
NOTICES_CACHE_SUBDIR = "notices"

#: Determines the subdir for notices cache
NOTICES_DECORATOR_DISPLAY_INTERVAL = 86400  # in seconds

DRY_RUN_PREFIX = "Dry run action:"
PREFIX_NAME_DISALLOWED_CHARS = {"/", " ", ":", "#"}


class SafetyChecks(Enum):
    disabled = "disabled"
    warn = "warn"
    enabled = "enabled"

    def __str__(self):
        return self.value


class PathConflict(Enum):
    clobber = "clobber"
    warn = "warn"
    prevent = "prevent"

    def __str__(self):
        return self.value


class DepsModifier(Enum):
    """Flags to enable alternate handling of dependencies."""
    NOT_SET = "not_set"  # default
    NO_DEPS = "no_deps"
    ONLY_DEPS = "only_deps"

    def __str__(self):
        return self.value


class UpdateModifier(Enum):
    SPECS_SATISFIED_SKIP_SOLVE = "specs_satisfied_skip_solve"
    FREEZE_INSTALLED = "freeze_installed"  # freeze is a better name for --no-update-deps
    UPDATE_DEPS = "update_deps"
    UPDATE_SPECS = "update_specs"  # default
    UPDATE_ALL = "update_all"

    def __str__(self):
        return self.value


class ValueEnum(Enum):
    """Subclass of enum that returns the value of the enum as its str representation"""

    def __str__(self):
        return f"{self.value}"


class ChannelPriority(ValueEnum):
    STRICT = "strict"
    # STRICT_OR_FLEXIBLE = "strict_or_flexible"  # TODO: consider implementing if needed
    FLEXIBLE = "flexible"
    DISABLED = "disabled"


class SatSolverChoice(ValueEnum):
    PYCOSAT = "pycosat"
    PYCRYPTOSAT = "pycryptosat"
    PYSAT = "pysat"


#: The name of the default solver, currently "classic"
DEFAULT_SOLVER = CLASSIC_SOLVER = "classic"


class NoticeLevel(ValueEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# Magic files for permissions determination
PACKAGE_CACHE_MAGIC_FILE = "urls.txt"
PREFIX_MAGIC_FILE = join("conda-meta", "history")

PREFIX_STATE_FILE = join("conda-meta", "state")
PACKAGE_ENV_VARS_DIR = join("etc", "conda", "env_vars.d")
CONDA_ENV_VARS_UNSET_VAR = "***unset***"


NAMESPACES_MAP = {  # base package name, namespace
    "python": "python",
    "r": "r",
    "r-base": "r",
    "mro-base": "r",
    "erlang": "erlang",
    "java": "java",
    "openjdk": "java",
    "julia": "julia",
    "latex": "latex",
    "lua": "lua",
    "nodejs": "js",
    "perl": "perl",
    "php": "php",
    "ruby": "ruby",
    "m2-base": "m2",
    "msys2-conda-epoch": "m2w64",
}

NAMESPACE_PACKAGE_NAMES = frozenset(NAMESPACES_MAP)
NAMESPACES = frozenset(NAMESPACES_MAP.values())
