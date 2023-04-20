from unittest.mock import MagicMock

from conda_config.context import create_context


def test_happy_path(tmp_path, base_condarc):
    """
    Makes sure that we can parse a correctly written condarc file
    """
    condarc_file = tmp_path / ".condarc"
    condarc_file.write_text(base_condarc)
    system_config = MagicMock(valid_condarc_files=[])
    context = create_context(system_config=system_config, extra_config_files=(condarc_file,))

    assert context.channels == ("conda-forge",)
    assert context.always_yes is True
    assert context.changeps1 is False


def test_happy_path_with_aliases(tmp_path, base_condarc_using_alias):
    """
    Makes sure that we can parse a correctly written condarc file when using aliases
    instead of the normal field value.
    """
    condarc_file = tmp_path / ".condarc"
    condarc_file.write_text(base_condarc_using_alias)
    system_config = MagicMock(valid_condarc_files=[])
    context = create_context(system_config=system_config, extra_config_files=(condarc_file,))

    assert context.channels == ("conda-forge",)

    assert context.always_yes is True
    assert context.changeps1 is False


def test_reading_from_environment_variables(base_condarc_using_env_vars):
    """
    Make sure that we can read from environment variables correctly, especially variables
    with a special delimiter value.
    """
    system_config = MagicMock(valid_config_files=[])
    context = create_context(system_config=system_config)

    assert context.pinned_packages == ("test_1", "test_2", "test_3")
    assert context.channels == ("defaults", "localhost", "testing")
    assert context.envs_dirs == ("/home/test", "/var/lib/test")
