from __future__ import annotations

import os
import pathlib
import warnings
from argparse import Namespace
from logging import getLogger
from collections.abc import Mapping
from pathlib import Path
from typing import Sequence, Any

from .condarc import CONDARC_ENV_VAR_NAME
from .constants import DEFAULTS_CHANNEL_NAME, LOCAL_CHANNEL_NAME
from .exceptions import ArgumentError, OperationNotAllowed
from .sources import ConfigSource, CLIConfigSource, FileConfigSource, ConfigFileTypes, EnvConfigSource
from .system import SystemConfiguration

#: Logger used to give warnings and errors
logger = getLogger(__name__)


class Context:
    """
    This object is meant to be defined as a singleton within this application
    and contains all configuration parameters for the application. These configuration
    parameters come from the following sources:

    - Environment variables
    - CLI arguments/options
    - Configuration files (i.e. ``condarc`` files)
    - System level configuration provided by the SystemConfiguration object

    Basically, it's your one-stop-shop for all things configurable! I'm still not
    sure that this is a good pattern to use. Here are some outstanding questions:

    - Will smashing all of these different sources together be confusing to future
      maintainers?
    - Is easy enough to understand the resolution order of configuration variables?
    - What if I just want direct access to the arguments object? How does that work?

    """

    #: Sequence holding all the different "ConfigSource" objects (i.e. classes that implement this
    #: abstract base class)
    _config_sources: Sequence[ConfigSource]

    #: SystemConfiguration object that holds specific information about the operating system
    #: and other environment specific things (e.g. prefix, conda environment name)
    _system_config: SystemConfiguration

    #: Determines the order of importance for our configuration sources
    CONFIG_PARSE_ORDER = ("cli", "env", "file")

    def __init__(
        self,
        system_config: SystemConfiguration,
        file_config_source: FileConfigSource = None,
        env_config_source: EnvConfigSource = None,
        cli_config_source: CLIConfigSource = None,
    ):
        """
        Creates the object responsible for gathering all application configuration.
        """
        self._file_config_source = file_config_source
        self._env_config_source = env_config_source
        self._cli_config_source = cli_config_source
        self._system_config = system_config

    def __getattr__(self, item) -> Any:
        """
        Overrides the default __getattr__ which allows for searching the ConfigSource
        type objects and the SystemConfiguration object for the additional values to return.
        This is done to make it convenient for us to access all of our configuration
        variables in a single object.

        The order in which the ConfigSource objects are passed in reflects their relative
        importance. The first variable definition we find is returned. We check the
        SystemConfiguration object last for variable definitions.

        Properties and attributes directly defined on the Context object will be returned
        before anything else.

        One nasty side effect this method has is that it gets called when we run across
        an AttributeError. This can lead to some weird, unexpected behavior in the class'
        methods.
        """
        # Used for collecting values which merge sequence and mapping types
        config_value_seq = ()
        config_value_map = {}

        for source in self.CONFIG_PARSE_ORDER:
            config_source = super().__getattribute__(f"_{source}_config_source")
            if config_source is not None:
                has_param = config_source.has_parameter(item)
                if has_param:
                    value = config_source.get_parameter(item)
                    if isinstance(value, tuple) or isinstance(value, list):
                        config_value_seq += tuple(value)
                    elif isinstance(value, dict):
                        config_value_map.update(value)
                    else:
                        return value

        # Return the first non-empty config_value_* variable.
        if config_value_seq:
            return config_value_seq
        elif config_value_map:
            return config_value_map

        if hasattr(self._system_config, item):
            return getattr(self._system_config, item)

        raise AttributeError(
            f"The following attribute '{item}' was not found on {self.__class__.__name__}, "
            f"{self.__class__.__name__}._config_sources or "
            f"{self.__class__.__name__}._system_config"
        )

    def _get_channel_names(self) -> tuple[str, ...]:
        """
        Channels can be stored as either a string or a mapping where the first and only
        key in this mapping is a channel name.

        Example:
            When we have the following condarc:
            ```
            channels:
              - defaults
              - http://localhost
                  type: local
            ```

            This method will return:
            ```
            ("defaults", "http://localhost")
            ```
        """
        channel_names = []

        for channel in self.__getattr__("channels"):
            if isinstance(channel, Mapping):
                keys = channel.keys()
                if len(keys) > 0:
                    name, *_ = keys
                    channel_names.append(name)
            else:
                channel_names.append(channel)

        return tuple(channel_names)

    @property
    def channels(self):
        """
        This is a special property that uses quite a bit of logic to retrieve the
        correct set of channels.
        """
        local_add = (LOCAL_CHANNEL_NAME,) if self.use_local else ()
        override_channels = self._cli_config_source.get_parameter("override_channels")
        channel = self._cli_config_source.get_parameter("channel")

        if override_channels:
            if not self.override_channels_enabled:
                raise OperationNotAllowed("Overriding channels has been disabled.")

            elif not channel:
                raise ArgumentError(
                    "At least one -c / --channel flag must be supplied when using "
                    "--override-channels."
                )
            else:
                return tuple(dict.fromkeys((*local_add, *channel)))

        if channel:
            channel_in_config_files = any(
                "channels" in data for _, data in self._file_config_source.raw_data
            )
            if not channel_in_config_files:
                return tuple(dict.fromkeys((*local_add, *channel, DEFAULTS_CHANNEL_NAME)))

            return tuple(dict.fromkeys(tuple(channel) + self._get_channel_names() + local_add))

        return tuple(dict.fromkeys(self._get_channel_names() + local_add))

    @property
    def channel_parameters(self):
        return self.__getattr__("channels")

    @property
    def experimental_solver(self):
        # TODO: Remove in a later release
        warnings.warn(
            "'context.experimental_solver' is pending deprecation and will be removed. "
            "Please consider using 'context.solver' instead.",
            PendingDeprecationWarning,
        )
        return self.__getattr__("solver")


def get_condarc_env_file(conda_env_var_name: str = CONDARC_ENV_VAR_NAME) -> Path | None:
    """
    We try to read the environment variable stored where CONDA_ENV_VAR_NAME specifies
    and then return a tuple Path object.
    """
    condarc_env_file = os.getenv(conda_env_var_name)

    if condarc_env_file is not None:
        condarc_file = pathlib.Path(condarc_env_file)

        if condarc_file.is_file():
            return condarc_file
        else:
            logger.warning(f'Unable to open "{CONDARC_ENV_VAR_NAME}" file: {condarc_file}')


def get_file_config_source(
    system_config: SystemConfiguration, extra_config_files: tuple[Path, ...] = None
) -> FileConfigSource:
    """
    Using a variety of sources, retrieves all locations where configuration files are stored
    and combines them into a single ``FileConfigSource`` object.
    """
    config_files = system_config.valid_condarc_files

    if extra_config_files is not None:
        config_files += extra_config_files

    condarc_env_file = get_condarc_env_file()

    if condarc_env_file:
        config_files += (condarc_env_file,)

    return FileConfigSource(ConfigFileTypes.yaml, config_files)


def create_context(
    args_obj: Namespace | None = None, extra_config_files: tuple[Path, ...] = None
) -> Context:
    """
    This function is responsible for constructing our Context object. It first collects
    configuration from a variety of sources and then uses the Context object to combine
    them all.

    :param args_obj: Namespace object that is created after parsing CLI arguments
    :param extra_config_files: Extra files, other than standard system locations, we want
                               to include; these override values from previous files.
    """
    system_config = SystemConfiguration()
    file_config_source = get_file_config_source(system_config, extra_config_files)

    args_obj = args_obj or Namespace()
    env_config_source = EnvConfigSource()
    cli_config_source = CLIConfigSource(args_obj)

    return Context(
        system_config,
        file_config_source=file_config_source,
        env_config_source=env_config_source,
        cli_config_source=cli_config_source,
    )
