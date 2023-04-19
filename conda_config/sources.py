from __future__ import annotations

import abc
import json
import logging
import os
from argparse import Namespace
from collections.abc import Sequence, Callable
from pathlib import Path
from typing import Any, Literal, Union

import ruamel.yaml as yaml

from .condarc import get_condarc_obj, CondarcConfig

logger = logging.getLogger(__name__)

ConfigFileTypes = Union[Literal["json"], Literal["yaml"]]


def _yaml_safe():
    parser = yaml.YAML(typ="safe", pure=True)
    parser.indent(mapping=2, offset=2, sequence=4)
    parser.default_flow_style = False
    return parser


def read_yaml_file(path: Path) -> dict[str, Any]:
    """
    Opens YAML file and returns value dictionary. If any errors are encountered opening
    the file or parsing the contents, we return an empty dictionary.
    """
    parsed_data = {}
    parser = _yaml_safe()

    try:
        with path.open("rb") as file_handle:
            try:
                parsed_data = parser.load(file_handle)
            except yaml.YAMLError as exc:
                logger.error(exc)
    except OSError as exc:
        logger.error(exc)

    return parsed_data


def read_json_file(path: Path) -> dict[str, Any]:
    """
    Opens JSON file and returns value dictionary. If any errors are encountered opening
    the file or parsing the contents, we return an empty dictionary.
    """
    parsed_data = {}

    try:
        with path.open("rb") as file_handle:
            try:
                parsed_data = json.load(file_handle)
            except ValueError as exc:
                logger.error(exc)
    except OSError as exc:
        logger.error(exc)

    return parsed_data


ConfigFileParserFunc = Callable[[Path], dict[str, Any]]


def get_config_file_parser(file_type: ConfigFileTypes) -> ConfigFileParserFunc:
    if file_type == "yaml":
        return read_yaml_file
    elif file_type == "json":
        return read_json_file
    else:
        raise NotImplemented(f"File type '{file_type}' is not currently supported")


class ConfigSource(abc.ABC):
    @abc.abstractmethod
    def get_parameter(self, name) -> Any:
        """Retrieves the named parameter from the configuration implementation"""

    @abc.abstractmethod
    def has_parameter(self, name) -> Any:
        """Determines whether the underlying storage object actually has this parameter"""


class FileConfigSource(ConfigSource):
    #: Type of file to parse
    file_type: ConfigFileTypes

    #: Parser that gets set from reading the ``file_type``
    file_parser: ConfigFileParserFunc

    #: List of configuration files to parse
    config_files: Sequence[Path]

    #: Object holding merged data from config files
    data: CondarcConfig

    def __init__(self, file_type: ConfigFileTypes, config_files: Sequence[Path]):
        """
        Creates a ConfigFileSource object that holds all the available config files.

        :param file_type: Determines the type of file parser that we set for this object
        :param config_files: List of a files to read configuration from. Order in which the files
                             are listed determines their relative importance (first ones overwrite
                             others).
        """
        self.file_type = file_type
        self.file_parser = get_config_file_parser(file_type)
        self.config_files = config_files

        # Expensive operation that loads all the different configuration files using
        # ``self.file_parser`` function that was deduced from the ``file_type``
        self.raw_data = tuple((path, self.file_parser(path)) for path in self.config_files)

        self.parsed_data = self._merge(self.config_files)

    def _merge(self, config_files: Sequence[Path]) -> CondarcConfig:
        if len(config_files) == 0:
            return CondarcConfig()
        return get_condarc_obj(self.raw_data)

    def get_parameter(self, name) -> Any:
        return getattr(self.parsed_data, name)

    def has_parameter(self, name) -> bool:
        return hasattr(self.parsed_data, name)


class EnvConfigSource(ConfigSource):
    COMMA_SEPARATED_PARAMS: set[str] = {
        "channels",
        "default_channels",
        "whitelist_channels",
        "migrated_channel_aliases",
        "repodata_fns",
        "pkgs_dirs",
        "aggressive_update_packages",
        "create_default_packages",
        "track_features",
    }

    COLON_SEPARATED_PARAMS: set[str] = {"envs_dirs", "envs_path", ""}

    AMP_SEPARATED_PARAMS: set[str] = {"disallowed_packages", "pinned_packages"}

    ENV_VAR_PREFIX = "CONDA_"

    def get_parameter(self, name) -> Any:
        value = os.getenv(f"{self.ENV_VAR_PREFIX}{name.upper()}")

        if value is not None:
            if name in self.COMMA_SEPARATED_PARAMS:
                return value.split(",")
            elif name in self.COLON_SEPARATED_PARAMS:
                return value.split(":")
            elif name in self.AMP_SEPARATED_PARAMS:
                return value.split("&")

        return value

    def has_parameter(self, name) -> bool:
        return f"{self.ENV_VAR_PREFIX}{name.upper()}" in os.environ


class CLIConfigSource(ConfigSource):
    """
    The primary purpose of this class is providing a consistent interface
    for our configuration sources.
    """

    #: This is the Namespace class from the argparse module
    args_obj: Namespace

    def __init__(self, args_obj: Namespace):
        """
        Sets the "args_obj" attribute. In the future this could also support different
        types of command line parsers (e.g. click or docopt)
        """
        self.args_obj = args_obj

    def get_parameter(self, name) -> Any:
        return getattr(self.args_obj, name, None)

    def has_parameter(self, name) -> bool:
        return hasattr(self.args_obj, name)
