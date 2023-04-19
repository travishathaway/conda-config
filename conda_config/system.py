# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from pathlib import Path
import platform
from typing import Sequence

from . import constants as const


class SystemConfiguration:
    """
    This is the system configuration object. It stores configuration that
    is specific to the type of system conda is running in (e.g. Windows vs.
    Linux).
    """

    #: Search path which determines where we find multiple `condarc` confiugrations
    search_path: Sequence[str]

    #: Users HOME directory
    home: str

    #: Users PATH variable
    path: str

    #: Shell the user is current running
    shell: str

    #: Determines whether we are running on Windows or not
    is_windows: bool

    #: Full path to your base conda install
    conda_root: str

    #: Full path to the current active environment
    conda_prefix: str

    #: Path to the currently configured conda executable
    conda_exe: str

    #: Path to the currently configured conda python executable
    conda_python_exe: str

    #: Path to the currently configured conda python executable
    conda_shlvl: int

    #: Name of the default environment (currently activated one)
    conda_default_env: int

    #: Override and point to a specific condarc file
    condarc: str

    #: Cuda related setting
    xdg_config_home: str

    #: Default path user's .condarc file
    user_rc_path: Path

    #: Default path for system .condarc file
    sys_rc_path: Path

    def __init__(self, **kwargs):
        """
        This method sets the default values for our properties. These mostly
        come from the environment and can be overridden.
        """
        # Set all the environment variables we care about
        self.home = kwargs.get("home") or os.getenv("HOME", "")
        self.path = kwargs.get("path") or os.getenv("PATH", "")
        self.shell = kwargs.get("shell") or os.getenv("SHELL", "")
        self.conda_root = kwargs.get("conda_root") or os.getenv("CONDA_ROOT", "")
        self.conda_prefix = kwargs.get("conda_prefix") or os.getenv("CONDA_PREFIX", "")
        self.conda_exe = kwargs.get("conda_exe") or os.getenv("CONDA_EXE", "")
        self.conda_python_exe = kwargs.get("conda_python_exe") or os.getenv("CONDA_PYTHON_EXE", "")
        self.conda_shlvl = kwargs.get("conda_shlvl") or os.getenv("CONDA_SHLVL", 1)
        self.conda_default_env = kwargs.get("conda_default_env") or os.getenv(
            "CONDA_DEFAULT_ENV", ""
        )
        self.condarc = kwargs.get("condarc") or os.getenv("CONDARC", "")
        self.xdg_config_home = kwargs.get("xdg_config_home") or os.getenv("XDG_CONFIG_HOME", "")
        self.user_rc_path = kwargs.get("user_rc_path") or (
            Path(os.path.abspath(os.path.expanduser("~/.condarc")))
        )
        self.sys_rc_path = kwargs.get("sys_rc_path") or (
            Path(os.path.join(sys.prefix, ".condarc"))
        )

        # Determine OS type
        self.is_windows = kwargs.get("is_windows") or (
            sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
        )

        # Setup search path for parsing condarc config files
        self.search_path = kwargs.get("search_path") or get_search_path_from_config(self)

    @property
    def valid_condarc_files(self) -> tuple[Path, ...]:
        """
        Using the search_path property, return a list of condarc files which actually exist"

        TODO: maybe cache this? This environment config is mutable, but I don't expect consumers
              to change anything after __post_init__ has run.
        """
        return tuple(
            Path(path_str)
            for path_str in self.search_path
            if os.path.exists(path_str) and os.path.isfile(path_str)
        )

    @property
    def default_channels(self) -> tuple[str, ...]:
        """We differ the default channels that configured depending on OS type"""
        return tuple(
            const.DEFAULT_CHANNELS_WIN if self.is_windows else const.DEFAULT_CHANNELS_UNIX
        )

    @property
    def compatible_shells(self) -> tuple[str, ...]:
        """Depending on which OS is currently configured, we'll want to display different shells"""
        return const.COMPATIBLE_SHELLS

    @property
    def platform(self) -> str:
        """Grab the platform we are using (wrapper around platform module)"""
        platform_name = platform.system().lower()

        if "darwin" in platform_name:
            return "osx"

        return platform_name


def get_search_path_from_config(config: SystemConfiguration) -> tuple[str, ...]:
    """
    Uses config parameters to determine the search path.
    """
    if config.is_windows:
        search_path = (
            "C:/ProgramData/conda/.condarc",
            "C:/ProgramData/conda/condarc",
            "C:/ProgramData/conda/condarc.d",
        )
    else:
        search_path = (
            "/etc/conda/.condarc",
            "/etc/conda/condarc",
            "/etc/conda/condarc.d/",
            "/var/lib/conda/.condarc",
            "/var/lib/conda/condarc",
            "/var/lib/conda/condarc.d/",
        )

    if config.conda_root:
        search_path += (
            os.path.join(config.conda_root, ".condarc"),
            os.path.join(config.conda_root, "condarc"),
            os.path.join(config.conda_root, "condarc.d"),
        )

    if config.xdg_config_home:
        search_path += (
            os.path.join(config.xdg_config_home, ".condarc"),
            os.path.join(config.xdg_config_home, "condarc"),
            os.path.join(config.xdg_config_home, "condarc.d"),
        )

    if config.conda_prefix:
        search_path += (
            os.path.join(config.conda_prefix, ".condarc"),
            os.path.join(config.conda_prefix, "condarc"),
            os.path.join(config.conda_prefix, "condarc.d"),
        )

    search_path += (
        os.path.join(config.home, ".config/conda/.condarc"),
        os.path.join(config.home, ".config/conda/condarc"),
        os.path.join(config.home, ".config/conda/condarc.d/"),
        os.path.join(config.home, ".conda/.condarc"),
        os.path.join(config.home, ".conda/condarc"),
        os.path.join(config.home, ".conda/condarc.d/"),
        os.path.join(config.home, ".condarc"),
        config.condarc,
    )

    return search_path
