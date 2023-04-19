from json import JSONDecodeError
from unittest.mock import MagicMock

import pytest
from ruamel.yaml import YAMLError

from conda_config import sources

#: Valid yaml
TEST_YAML_FILE_VALID_ONE = """
channels:
  - conda-forge
always_yes: true
"""

TEST_YAML_FILE_VALID_TWO = """
channels:
  - defaults
always_yes: false
"""

#: Valid json
TEST_JSON_FILE_VALID = """{
  "channels": [
    "defaults",
    "conda-forge"
  ],
  "always_yes": true
}
"""


def test_read_yaml_file_success(tmpdir):
    """
    Tests a successful opening of a yaml file
    """
    yaml_file = tmpdir.join("test.yaml")
    yaml_file.write(TEST_YAML_FILE_VALID_ONE)

    content = sources.read_yaml_file(yaml_file)

    assert content["channels"] == ["conda-forge"]
    assert content["always_yes"] is True


def test_read_yaml_file_read_error():
    """
    Tests a failed opening of a yaml file
    """
    path = MagicMock()
    path.open = MagicMock(side_effect=PermissionError("Unable to open file"))

    content = sources.read_yaml_file(path)

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


def test_read_json_file_success(tmpdir):
    """
    Tests a successful opening of a json file
    """
    json_file = tmpdir.join("test.json")
    json_file.write(TEST_JSON_FILE_VALID)

    content = sources.read_json_file(json_file)

    assert content["channels"] == ["defaults", "conda-forge"]
    assert content["always_yes"] is True


def test_read_json_file_read_error():
    """
    Tests a failed opening of a json file
    """
    path = MagicMock()
    path.open = MagicMock(side_effect=PermissionError("Unable to open file"))

    content = sources.read_json_file(path)

    assert content == {}


def test_read_json_file_json_error(tmpdir, mocker):
    """
    Tests a failed opening of a json file
    """
    json_file = tmpdir.join("test.json")
    json_file.write(TEST_JSON_FILE_VALID)

    parser = mocker.patch("conda_config.sources.json")
    parser.load = MagicMock(side_effect=JSONDecodeError("Error parsing JSON", json_file.read(), 1))

    content = sources.read_json_file(json_file)

    assert content == {}


def test_file_config_source(tmpdir):
    yaml_file_one = tmpdir.join("test_one.yaml")
    yaml_file_one.write(TEST_YAML_FILE_VALID_ONE)

    yaml_file_two = tmpdir.join("test_two.yaml")
    yaml_file_two.write(TEST_YAML_FILE_VALID_TWO)

    file_source = sources.FileConfigSource("yaml", [yaml_file_one, yaml_file_two])

    assert file_source.has_parameter("always_yes") is True
    assert file_source.get_parameter("always_yes") is False
