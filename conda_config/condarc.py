from __future__ import annotations

import logging
from collections.abc import Sequence
from functools import reduce
from pathlib import Path
from typing import Literal, Any, Tuple, Dict, Union

from pydantic import BaseSettings, Field, ValidationError

from .exceptions import CondaConfigError
from .errors import (
    format_validation_error,
    format_all_validation_errors,
    CONFIG_ERROR_PREFIX,
)

logger = logging.getLogger(__name__)

#: These are the multiple names that certain fields can have
FIELD_ALIASES = {
    "channel": "channels",
    "add_binstar_token": "add_anaconda_token",
    "envs_path": "envs_dirs",
    "client_cert": "client_ssl_cert",
    "client_cert_key": "client_ssl_cert_key",
    "verify_ssl": "ssl_verify",
    "self_update": "auto_update_conda",
    "disallow": "disallowed_packages",
    "copy": "always_copy",
    "softlink": "always_softlink",
    "binstar_upload": "anaconda_upload",
    "conda-build": "conda_build",
    "yes": "always_yes",
    "json": "json__",
    "verbose": "verbosity",
    "solver": "experimental_solver",
}

#: Name of the environment variable which stores path to config file
#: that will override current configuration settings.
CONDARC_ENV_VAR_NAME = "CONDARC_NEW"


def merge_condarc(obj_one: CondarcConfig, obj_two: CondarcConfig) -> CondarcConfig:
    """
    Provided two CondaRC objects, return one where right (obj_two) overrides properties
    on left (obj_one).

    Depending on the type of object we receive, we use a different merging mechanism:

    - tuple: concatenate and ensure the values are unique
    - dict: merged together
    - str, int, bool: obj_two overrides obj_one
    """
    merged_values: dict[str, Any] = {}

    for fld, value in obj_two.dict().items():
        if isinstance(value, tuple):
            merged_values[fld] = tuple(
                dict.fromkeys(value + getattr(obj_one, fld, tuple()))
            )
        elif isinstance(value, dict):
            value.update(getattr(obj_one, fld))
            merged_values[fld] = value
        else:
            merged_values[fld] = value if value is not None else getattr(obj_one, fld)

    return CondarcConfig(**merged_values)


def remap_aliases(config: dict[str, Any]) -> None:
    """
    This function exists because pydantic does not currently support multiple alias
    values. To get over this, we remap the values ourselves before passing this to our
    pydantic model. This should be removed an upgraded once V2 is released. More information
    about multiple aliases can be found here:

    - https://pydantic-docs.helpmanual.io/blog/pydantic-v2/#more-powerful-aliases
    """
    for alias, field_name in FIELD_ALIASES.items():
        if alias in config:
            config[field_name] = config.pop(alias)


def get_condarc_obj(config_data: Sequence[tuple[Path, dict]]) -> CondarcConfig:
    """
    From a tuple of (Path, dict) objects where dict is the parsed data, perform the
    desired merge operation and return a single CondaRC object.

    :raises CondaConfigError: Thrown if we run across validation errors while parsing

    TODO: this function needs to be able to respect the !final, !top and !bottom directives
          found in comments.
    """
    condarc_configs: list[CondarcConfig] = []
    validation_errors: list[str] = []

    for path, single_config in config_data:
        # If this is a string value, we know we didn't parse it correctly
        if isinstance(single_config, str):
            validation_errors.append(f"{CONFIG_ERROR_PREFIX}: {path}")
            continue

        remap_aliases(single_config)

        try:
            config = CondarcConfig(**single_config)
            condarc_configs.append(config)
        except ValidationError as exc:
            validation_errors.append(format_validation_error(exc, path))

    if len(validation_errors) > 0:
        raise CondaConfigError(format_all_validation_errors(validation_errors))

    return reduce(merge_condarc, condarc_configs)


class CondarcConfig(BaseSettings):
    """
    Contains all variables which come from the condarc file
    """

    ####################################################
    #              Channel Configuration               #
    ####################################################

    channels: Tuple[Union[str, Dict[str, Dict[str, str]]], ...] = Field(
        default=("defaults",),
        description="""
        **aliases** -> channel

        **env_var_string_delimiter** ->  ','

        The list of conda channels to include for relevant operations.
        """,
    )

    channel_alias: str = Field(
        default="https://conda.anaconda.org",
        description="""
        The prepended url location to associate with channel names.
        """,
    )

    default_channels: Tuple[str, ...] = Field(
        default=(
            "https://repo.anaconda.com/pkgs/main",
            "https://repo.anaconda.com/pkgs/r",
        ),
        description="""
        **env_var_string_delimiter** ->  ','

        The list of channel names and/or urls used for the 'defaults'
        multichannel.
        """,
    )

    override_channels_enabled: bool = Field(
        default=True,
        description="""
        Permit use of the --overide-channels command-line flag.
        """,
    )

    use_local: bool = Field(
        default=False,
        description="""
        Only use local channels for all commands.
        """,
    )

    allowlist_channels: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
    **env_var_string_delimiter** ->  ','

    The exclusive list of channels allowed to be used on the system. Use
    of any other channels will result in an error. If conda-build channels
    are to be allowed, along with the --use-local command line flag, be
    sure to include the 'local' channel in the list. If the list is empty
    or left undefined, no channel exclusions will be enforced.
    """,
    )

    custom_channels: Dict[str, str] = Field(
        default={"pkgs/pro": "https://repo.anaconda.com"},
        description="""
        A map of key-value pairs where the key is a channel name and the value
        is a channel location. Channels defined here override the default
        'channel_alias' value. The channel name (key) is not included in the
        channel location (value).  For example, to override the location of
        the 'conda-forge' channel where the url to repodata is
        https://anaconda-repo.dev/packages/conda-forge/linux-64/repodata.json,
        add an entry 'conda-forge: https://anaconda-repo.dev/packages'.
        """,
    )

    custom_multichannels: Dict[str, Tuple[str, ...]] = Field(
        default_factory=dict,
        description="""
        A multichannel is a metachannel composed of multiple channels. The two
        reserved multichannels are 'defaults' and 'local'. The 'defaults'
        multichannel is customized using the 'default_channels' parameter. The
        'local' multichannel is a list of file:// channel locations where
        conda-build stashes successfully-built packages.  Other multichannels
        can be defined with custom_multichannels, where the key is the
        multichannel name and the value is a list of channel names and/or
        channel urls.
        """,
    )

    migrated_channel_aliases: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
        **env_var_string_delimiter** ->  ','

        A list of previously-used channel_alias values. Useful when switching
        between different Anaconda Repository instances.
        """,
    )

    migrated_custom_channels: Dict[str, str] = Field(
        default_factory=dict,
        description="""
        A map of key-value pairs where the key is a channel name and the value
        is the previous location of the channel.
        """,
    )

    add_anaconda_token: bool = Field(
        default=True,
        description="""
        **aliases** -> add_binstar_token

        In conjunction with the anaconda command-line client (installed with
        `conda install anaconda-client`), and following logging into an
        Anaconda Server API site using `anaconda login`, automatically apply a
        matching private token to enable access to private packages and
        channels.
        """,
    )

    allow_non_channel_urls: bool = Field(
        default=False,
        description="""
        Warn, but do not fail, when conda detects a channel url is not a valid
        channel.
        """,
    )

    restore_free_channel: bool = Field(
        default=False,
        description="""
        "Add the "free" channel back into defaults, behind "main" in priority.
        The "free" channel was removed from the collection of default channels
        in conda 4.7.0.
        """,
    )

    repodata_fns: Tuple[str, ...] = Field(
        default=("current_repodata.json", "repodata.json"),
        description="""
        **env_var_string_delimiter** ->  ','

        Specify filenames for repodata fetching. The default is
        ('current_repodata.json', 'repodata.json'), which tries a subset of
        the full index containing only the latest version for each package,
        then falls back to repodata.json.  You may want to specify something
        else to use an alternate index that has been reduced somehow.
        """,
    )

    use_only_tar_bz2: Union[bool, None] = Field(
        default=None,
        description="""
        A boolean indicating that only .tar.bz2 conda packages should be
        downloaded. This is forced to True if conda-build is installed and
        older than 3.18.3, because older versions of conda break when conda
        feeds it the new file format.
        """,
    )

    repodata_threads: int = Field(
        default=0,
        description="""
        Threads to use when downloading and reading repodata.  When not set,
        defaults to None, which uses the default ThreadPoolExecutor behavior.
        """,
    )

    ####################################################
    #            Basic Conda Configuration             #
    ####################################################

    envs_dirs: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
        **aliases** -> envs_path

        **env_var_string_delimiter** ->  ':'

        The list of directories to search for named environments. When
        creating a new named environment, the environment will be placed in
        the first writable location.
        """,
    )

    pkgs_dirs: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
        **env_var_string_delimiter** ->  ','

        The list of directories where locally-available packages are linked
        from at install time. Packages not locally available are downloaded
        and extracted into the first writable directory.
        """,
    )

    default_threads: int = Field(
        default=0,
        description="""
        Threads to use by default for parallel operations.  Default is None,
        which allows operations to choose themselves.  For more specific
        control, see the other *_threads parameters:     * repodata_threads -
        for fetching/loading repodata     * verify_threads - for verifying
        package contents in transactions     * execute_threads - for carrying
        out the unlinking and linking steps
        """,
    )

    ####################################################
    #              Network Configuration               #
    ####################################################

    client_ssl_cert: str = Field(
        default=None,
        description="""
        **aliases** -> client_cert

        A path to a single file containing a private key and certificate (e.g.
        .pem file). Alternately, use client_ssl_cert_key in conjunction with
        client_ssl_cert for individual files.
        """,
    )

    client_ssl_cert_key: str = Field(
        default=None,
        description="""
        **aliases** -> client_cert_key

        Used in conjunction with client_ssl_cert for a matching key file.
        """,
    )

    local_repodata_ttl: Union[int, bool] = Field(
        default=1,
        description="""
        For a value of False or 0, always fetch remote repodata (HTTP 304
        responses respected). For a value of True or 1, respect the HTTP
        Cache-Control max-age header. Any other positive integer values is the
        number of seconds to locally cache repodata before checking the remote
        server for an update.
        """,
    )

    offline: bool = Field(
        default=False,
        description="""
        Restrict conda to cached download content and file:// based urls.
        """,
    )

    proxy_servers: Dict[str, str] = Field(
        default_factory=dict,
        description="""
        A mapping to enable proxy settings. Keys can be either (1) a
        scheme://hostname form, which will match any request to the given
        scheme and exact hostname, or (2) just a scheme, which will match
        requests to that scheme. Values are are the actual proxy server, and
        are of the form 'scheme://[user:password@]host[:port]'. The optional
        'user:password' inclusion enables HTTP Basic Auth with your proxy.
        """,
    )

    remote_connect_timeout_secs: float = Field(
        default=9.15,
        description="""
        The number seconds conda will wait for your client to establish a
        connection to a remote url resource.
        """,
    )

    remote_max_retries: int = Field(
        default=3,
        description="""
        The maximum number of retries each HTTP connection should attempt.
        """,
    )

    remote_backoff_factor: int = Field(
        default=1,
        description="""
        The factor determines the time HTTP connection should wait for
        attempt.
        """,
    )

    remote_read_timeout_secs: float = Field(
        default=60.0,
        description="""
        Once conda has connected to a remote resource and sent an HTTP
        request, the read timeout is the number of seconds conda will wait for
        the server to send a response.
        """,
    )

    ssl_verify: bool = Field(
        default=True,
        description="""
        **aliases** -> verify_ssl

        Conda verifies SSL certificates for HTTPS requests, just like a web
        browser. By default, SSL verification is enabled, and conda operations
        will fail if a required url's certificate cannot be verified. Setting
        ssl_verify to False disables certification verification. The value for
        ssl_verify can also be (1) a path to a CA bundle file, or (2) a path
        to a directory containing certificates of trusted CA.
        """,
    )

    ####################################################
    #               Solver Configuration               #
    ####################################################

    aggressive_update_packages: Tuple[str, ...] = Field(
        default=("ca-certificates", "certifi", "openssl"),
        description="""
        **env_var_string_delimiter** ->  ','

        A list of packages that, if installed, are always updated to the
        latest possible version.
        """,
    )

    auto_update_conda: bool = Field(
        default=True,
        description="""
        **aliases** -> self_update

        Automatically update conda when a newer or higher priority version is
        detected.
        """,
    )

    channel_priority: Literal["flexible", "strict", "disabled"] = Field(
        default="flexible",
        description="""
        Accepts values of 'strict', 'flexible', and 'disabled'. The default
        value is 'flexible'. With strict channel priority, packages in lower
        priority channels are not considered if a package with the same name
        appears in a higher priority channel. With flexible channel priority,
        the solver may reach into lower priority channels to fulfill
        dependencies, rather than raising an unsatisfiable error. With channel
        priority disabled, package version takes precedence, and the
        configured priority of channels is used only to break ties. In
        previous versions of conda, this parameter was configured as either
        True or False. True is now an alias to 'flexible'.
        """,
    )

    create_default_packages: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
        **env_var_string_delimiter** ->  ','

        Packages that are by default added to a newly created environments.
        """,
    )

    disallowed_packages: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
        **aliases** -> disallow

        **env_var_string_delimiter** ->  '&'

        Package specifications to disallow installing. The default is to allow
        all packages.
        """,
    )

    force_reinstall: bool = Field(
        default=False,
        description="""
        Ensure that any user-requested package for the current operation is
        uninstalled and reinstalled, even if that package already exists in
        the environment.
        """,
    )

    pinned_packages: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
        **env_var_string_delimiter** ->  '&'

        A list of package specs to pin for every environment resolution. This
        parameter is in BETA, and its behavior may change in a future release.
        """,
    )

    pip_interop_enabled: bool = Field(
        default=False,
        description="""
        Allow the conda solver to interact with non-conda-installed python
        packages.
        """,
    )

    track_features: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="""
        **env_var_string_delimiter** -> ','

        A list of features that are tracked by default. An entry here is
        similar to adding an entry to the create_default_packages list.
        """,
    )

    solver: str = Field(
        default="classic",
        description="""
        A string to choose between the different solver logics implemented in
        conda. A solver logic takes care of turning your requested packages
        into a list of specs to add and/or remove from a given environment,
        based on their dependencies and specified constraints.
        """,
    )

    ####################################################
    #  Package Linking and Install-time Configuration  #
    ####################################################

    allow_softlinks: bool = Field(
        default=False,
        description="""
        When allow_softlinks is True, conda uses hard-links when possible, and
        soft-links (symlinks) when hard-links are not possible, such as when
        installing on a different filesystem than the one that the package
        cache is on. When allow_softlinks is False, conda still uses hard-
        links when possible, but when it is not possible, conda copies files.
        Individual packages can override this setting, specifying that certain
        files should never be soft-linked (see the no_link option in the build
        recipe documentation).
        """,
    )

    always_copy: bool = Field(
        default=False,
        description="""
        **aliases** -> copy

        Register a preference that files be copied into a prefix during
        install rather than hard-linked.
        """,
    )

    always_softlink: bool = Field(
        default=False,
        description="""
        **aliases** -> softlink

        Register a preference that files be soft-linked (symlinked) into a
        prefix during install rather than hard-linked. The link source is the
        'pkgs_dir' package cache from where the package is being linked.
        WARNING: Using this option can result in corruption of long-lived
        conda environments. Package caches are *caches*, which means there is
        some churn and invalidation. With this option, the contents of
        environments can be switched out (or erased) via operations on other
        environments.
        """,
    )

    path_conflict: Literal["clobber", "warn", "prevent"] = Field(
        default="clobber",
        description="""
        The method by which conda handle's conflicting/overlapping paths
        during a create, install, or update operation. The value must be one
        of 'clobber', 'warn', or 'prevent'. The '--clobber' command-line flag
        or clobber configuration parameter overrides path_conflict set to
        'prevent'.
        """,
    )

    rollback_enabled: bool = Field(
        default=True,
        description="""
        Should any error occur during an unlink/link transaction, revert any
        disk mutations made to that point in the transaction.
        """,
    )

    safety_checks: Literal["warn", "enabled", "disabled"] = Field(
        default="warn",
        description="""
        Enforce available safety guarantees during package installation. The
        value must be one of 'enabled', 'warn', or 'disabled'.
        """,
    )

    extra_safety_checks: bool = Field(
        default=False,
        description="""
        Spend extra time validating package contents.  Currently, runs sha256
        verification on every file within each package during installation.
        """,
    )

    signing_metadata_url_base: str = Field(
        default=None,
        description="""
        Base URL for obtaining trust metadata updates (i.e., the `*.root.json`
        and `key_mgr.json` files) used to verify metadata and (eventually)
        package signatures.
        """,
    )

    shortcuts: bool = Field(
        default=True,
        description="""
        Allow packages to create OS-specific shortcuts (e.g. in the Windows
        Start Menu) at install time.
        """,
    )

    non_admin_enabled: bool = Field(
        default=True,
        description="""
        Allows completion of conda's create, install, update, and remove
        operations, for non-privileged (non-root or non-administrator) users.
        """,
    )

    separate_format_cache: bool = Field(
        default=False,
        description="""
        Treat .tar.bz2 files as different from .conda packages when filenames
        are otherwise similar. This defaults to False, so that your package
        cache doesn't churn when rolling out the new package format. If you'd
        rather not assume that a .tar.bz2 and .conda from the same place
        represent the same content, set this to True.
        """,
    )

    verify_threads: int = Field(
        default=0,
        description="""
        Threads to use when performing the transaction verification step.
        When not set, defaults to 1.
        """,
    )

    execute_threads: int = Field(
        default=0,
        description="""
        Threads to use when performing the unlink/link transaction.  When not
        set, defaults to 1.  This step is pretty strongly I/O limited, and you
        may not see much benefit here.
        """,
    )

    ####################################################
    #            Conda-build Configuration             #
    ####################################################

    bld_path: str = Field(
        default="",
        description="""
        The location where conda-build will put built packages. Same as
        'croot', but 'croot' takes precedence when both are defined. Also used
        in construction of the 'local' multichannel.
        """,
    )

    croot: str = Field(
        default="",
        description="""
        The location where conda-build will put built packages. Same as
        'bld_path', but 'croot' takes precedence when both are defined. Also
        used in construction of the 'local' multichannel.
        """,
    )

    anaconda_upload: bool = Field(
        default=False,
        description="""
        **aliases** -> binstar_upload

        Automatically upload packages built with conda build to anaconda.org.
        """,
    )

    conda_build: dict = Field(
        default_factory=dict,
        description="""
        **aliases** -> conda-build

        General configuration parameters for conda-build.
        """,
    )

    ####################################################
    #  Output, Prompt, and Flow Control Configuration  #
    ####################################################

    always_yes: bool = Field(
        default=False,
        description="""
        **aliases** -> yes

        Automatically choose the 'yes' option whenever asked to proceed with a
        conda operation, such as when running `conda install`.
        """,
    )

    auto_activate_base: bool = Field(
        default=True,
        description="""
        Automatically activate the base environment during shell
        initialization.
        """,
    )

    auto_stack: int = Field(
        default=0,
        description="""
        Implicitly use --stack when using activate if current level of nesting
        (as indicated by CONDA_SHLVL environment variable) is less than or
        equal to specified value. 0 or false disables automatic stacking, 1 or
        true enables it for one level.
        """,
    )

    changeps1: bool = Field(
        default=True,
        description="""
        When using activate, change the command prompt ($PS1) to include the
        activated environment.
        """,
    )

    env_prompt: str = Field(
        default="({default_env})",
        description="""
        Template for prompt modification based on the active environment.
        Currently supported template variables are '{prefix}', '{name}', and
        '{default_env}'. '{prefix}' is the absolute path to the active
        environment. '{name}' is the basename of the active environment
        prefix. '{default_env}' holds the value of '{name}' if the active
        environment is a conda named environment ('-n' flag), or otherwise
        holds the value of '{prefix}'. Templating uses python's str.format()
        method.
        """,
    )

    json__: bool = Field(
        default=False,
        description="""
        Ensure all output written to stdout is structured json.
        """,
    )

    notify_outdated_conda: bool = Field(
        default=True,
        description="""
        Notify if a newer version of conda is detected during a create,
        install, update, or remove operation.
        """,
    )

    quiet: bool = Field(
        default=False,
        description="""
        Disable progress bar display and other output.
        """,
    )

    report_errors: bool = Field(
        default=False,
        description="""
        Opt in, or opt out, of automatic error reporting to core maintainers.
        Error reports are anonymous, with only the error stack trace and
        information given by `conda info` being sent.
        """,
    )

    show_channel_urls: bool = Field(
        default=None,
        description="""
        Show channel URLs when displaying what is going to be downloaded.
        """,
    )

    verbosity: int = Field(
        default=0,
        description="""
        **aliases** -> verbose

        Sets output log level. 0 is warn. 1 is info. 2 is debug. 3 is trace.
        """,
    )

    unsatisfiable_hints: bool = Field(
        default=True,
        description="""
        A boolean to determine if conda should find conflicting packages in
        the case of a failed install.
        """,
    )

    unsatisfiable_hints_check_depth: int = Field(
        default=2,
        description="""
        An integer that specifies how many levels deep to search for
        unsatisfiable dependencies. If this number is 1 it will complete the
        unsatisfiable hints fastest (but perhaps not the most complete). The
        higher this number, the longer the generation of the unsat hint will
        take. Defaults to 3.
        """,
    )

    # class Config:
    #     env_prefix = "CONDA_"
    #     env_nested_delimiter = ","  # Default delimiter, others are specified below

    #     # TODO: not happy with having to define this set. It would be nice to be
    #     # able to define multiple delimiters or better, define this directly on the
    #     # field itself.
    #     comma_delimited_fields: set[str] = {
    #         "channels",
    #         "default_channels",
    #         "allowlist_channels",
    #         "migrated_channel_aliases",
    #         "repodata_fns",
    #         "pkgs_dirs",
    #         "aggressive_update_packages",
    #         "create_default_packages",
    #         "track_features",
    #     }

    #     colon_delimited_field = "envs_dirs"

    #     amp_delimited_fields: set[str] = {"disallowed_packages", "pinned_packages"}

    #     @classmethod
    #     def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
    #         if field_name in cls.comma_delimited_fields:
    #             return raw_val.split(",")
    #         elif field_name in cls.amp_delimited_fields:
    #             return raw_val.split("&")
    #         elif field_name == cls.colon_delimited_field:
    #             return raw_val.split(":")
    #         return cls.json_loads(raw_val)
