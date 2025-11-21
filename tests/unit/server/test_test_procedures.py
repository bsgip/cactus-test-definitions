from importlib import resources
from pathlib import Path

import pytest
from assertical.asserts.type import assert_dict_type
from cactus_test_definitions.server.test_procedures import (
    TestProcedure,
    TestProcedureId,
    get_all_test_procedures,
    parse_test_procedure,
)
from dataclass_wizard.errors import UnknownKeysError


def test_TestProcedureId_synchronised():
    """Ensures that TestProcedureId is in sync with all available TestProcedures YAML files.

    Each MY-TEST.yaml must have a corresponding TestProcedureId.MY_TEST"""

    # Discover all the YAML files
    suffix = ".yaml"
    raw_file_names: set[str] = set()
    for yaml_file in resources.files("cactus_test_definitions.server.procedures").iterdir():
        if yaml_file.is_file() and yaml_file.name.endswith(suffix):
            raw_file_names.add(yaml_file.name[: -len(suffix)])

    # Compare them against the TestProcedureId
    for file_name in raw_file_names:
        assert file_name in TestProcedureId
    for tp_id in TestProcedureId:
        assert tp_id in raw_file_names
    assert len(raw_file_names) == len(TestProcedureId)


def test_available_tests_populated():
    """Force test procedures to load and ensure they all validate (and we at least have a few)"""

    all_tps = get_all_test_procedures()
    assert_dict_type(TestProcedureId, TestProcedure, all_tps, count=len(TestProcedureId))
    assert all_tps[TestProcedureId.S_ALL_01] != all_tps[TestProcedureId.S_ALL_02], "Sanity check on uniqueness"


def test_error_on_duplicate_key():
    """Force test procedures to load and ensure they all validate (and we at least have a few)"""

    with open(Path("tests/data/server/tp_error_duplicate_keys.yaml"), "r") as fp:
        yaml_contents = fp.read()

    with pytest.raises(ValueError):
        parse_test_procedure(yaml_contents)


def test_error_on_extra_key():
    """Force test procedures to load and ensure they all validate (and we at least have a few)"""

    with open(Path("tests/data/server/tp_error_extra_keys.yaml"), "r") as fp:
        yaml_contents = fp.read()

    with pytest.raises(UnknownKeysError):
        parse_test_procedure(yaml_contents)
