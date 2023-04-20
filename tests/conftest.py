import pytest


BASE_CONDARC = """
channels:
    - conda-forge
always_yes: yes
changeps1: no
"""

BASE_CONDARC_USING_ALIAS = """
channel:
    - conda-forge
yes: yes
changeps1: no
"""


@pytest.fixture()
def base_condarc():
    yield BASE_CONDARC


@pytest.fixture()
def base_condarc_using_alias():
    yield BASE_CONDARC_USING_ALIAS


@pytest.fixture()
def base_condarc_using_env_vars(monkeypatch):
    monkeypatch.setenv("CONDA_CHANNELS", "defaults,localhost,testing")
    monkeypatch.setenv("CONDA_PINNED_PACKAGES", "test_1&test_2&test_3")
    monkeypatch.setenv("CONDA_ENVS_DIRS", "/home/test:/var/lib/test")
