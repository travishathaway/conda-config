from argparse import Namespace
from json import JSONDecodeError
from unittest.mock import MagicMock

import pytest

from ruamel.yaml import YAMLError

from conda_config import sources

#: Valid yaml
TEST_YAML_FILE_VALID_ONE = """
channels:
  - conda-forge
always_yes: false
"""

TEST_YAML_FILE_VALID_TWO = """
channels:
  - defaults
always_yes: true
"""

#: Valid json
TEST_JSON_FILE_VALID_ONE = """{
  "channels": [
    "conda-forge"
  ],
  "always_yes": false
}
"""

TEST_JSON_FILE_VALID_TWO = """{
  "channels": [
    "defaults"
  ],
  "always_yes": true
}
"""


@pytest.mark.parametrize(
    "contents,name, function",
    (
        (TEST_YAML_FILE_VALID_ONE, "test.yaml", sources.read_yaml_file),
        (TEST_JSON_FILE_VALID_ONE, "test.json", sources.read_json_file),
    ),
)
def test_read_file_success(tmpdir, contents, name, function):
    """
    Tests a successful opening with various file type parsing functions.
    """
    file = tmpdir.join(name)
    file.write(contents)

    content = function(file)

    assert content["channels"] == ["conda-forge"]
    assert content["always_yes"] is False


@pytest.mark.parametrize(
    "function",
    (
        sources.read_json_file,
        sources.read_yaml_file,
    ),
)
def test_file_read_error(function):
    """
    Tests a failed opening of file with various file parsers.
    """
    path = MagicMock()
    path.open = MagicMock(side_effect=PermissionError("Unable to open file"))

    content = function(path)

    assert content == {}


def test_read_yaml_file_yaml_error(tmpdir, mocker):
    """
    Tests a failed opening of a yaml file
    """
    yaml_file = tmpdir.join("test.yaml")
    yaml_file.write(TEST_YAML_FILE_VALID_ONE)

    parser = mocker.patch("conda_config.sources._yaml_safe")
    parser().load = MagicMock(side_effect=YAMLError("Error parsing YAML"))

    content = sources.read_yaml_file(yaml_file)

    assert content == {}


def test_read_json_file_json_error(tmpdir, mocker):
    """
    Tests a failed opening of a json file
    """
    json_file = tmpdir.join("test.json")
    json_file.write(TEST_JSON_FILE_VALID_ONE)

    parser = mocker.patch("conda_config.sources.json")
    parser.load = MagicMock(
        side_effect=JSONDecodeError("Error parsing JSON", json_file.read(), 1)
    )

    content = sources.read_json_file(json_file)

    assert content == {}


def test_file_config_source_no_files():
    """
    Test to make sure that everything still works when we pass an empty list of files.

    The assertions are relying on the default values for the CondarcConfig Pydantic model.
    """
    file_source = sources.FileConfigSource("yaml", [])

    assert file_source.has_parameter("channels") is True
    assert file_source.get_parameter("channels") == ("defaults",)


@pytest.mark.parametrize(
    "file_contents,file_names, file_type",
    (
        (
            (TEST_YAML_FILE_VALID_ONE, TEST_YAML_FILE_VALID_TWO),
            ("test_one.yaml", "test_two.yaml"),
            "yaml",
        ),
        (
            (TEST_JSON_FILE_VALID_ONE, TEST_JSON_FILE_VALID_TWO),
            ("test_one.json", "test_two.json"),
            "json",
        ),
    ),
)
def test_file_config_source_yaml(tmpdir, file_contents, file_names, file_type):
    """
    Test using two separate configuration files. We need to make sure that the
    values are being appropriately overriden. The second file should override
    settings from the first for string, int and boolean values and sequences
    should be merged together.
    """
    name_one, name_two = file_names
    content_one, content_two = file_contents

    file_one = tmpdir.join(name_one)
    file_one.write(content_one)
    file_two = tmpdir.join(name_two)
    file_two.write(content_two)

    file_source = sources.FileConfigSource(file_type, [file_one, file_two])

    assert file_source.has_parameter("always_yes") is True
    assert file_source.get_parameter("always_yes") is True

    assert file_source.has_parameter("channels") is True
    assert file_source.get_parameter("channels") == ("defaults", "conda-forge")


def test_file_config_source_bad_file_type():
    """
    Makes sure that a `NotImplemented` error is raised when we pass in an invalid file type
    """
    bad_file_type = "docx"

    with pytest.raises(
        NotImplementedError,
        match=f"File type '{bad_file_type}' is not currently supported",
    ):
        sources.get_config_file_parser(bad_file_type)


def test_cli_config_source():
    """
    Simple tests for the CLIConfigSource class
    """
    args = Namespace()
    args.field_one = "value"
    args.field_two = ["value", "two"]

    cli_source = sources.CLIConfigSource(args_obj=args)

    assert cli_source.has_parameter("field_one") is True
    assert cli_source.get_parameter("field_one") == "value"

    assert cli_source.has_parameter("field_two") is True
    assert cli_source.get_parameter("field_two") == ["value", "two"]


@pytest.mark.parametrize(
    "field,value,expected",
    (
        ("channels", "bioconda,nvidia", ["bioconda", "nvidia"]),
        (
            "envs_dirs",
            "/opt/folder_one:/opt/folder_two",
            ["/opt/folder_one", "/opt/folder_two"],
        ),
        (
            "disallowed_packages",
            "package_one&package_two",
            ["package_one", "package_two"],
        ),
        ("repodata_threads", "4", "4"),
    ),
)
def test_env_config_source_with_channels(monkeypatch, field, value, expected):
    """
    Simple tests for the CLIConfigSource class
    """
    monkeypatch.setenv(f"CONDA_{field.upper()}", value)

    env_source = sources.EnvConfigSource()

    assert env_source.has_parameter(field) is True
    assert env_source.get_parameter(field) == expected
