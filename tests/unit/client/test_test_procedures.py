from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path

import pytest
from assertical.asserts.type import assert_dict_type
from cactus_test_definitions.client.test_procedures import (
    TestProcedure,
    TestProcedureId,
    get_all_test_procedures,
    parse_test_procedure,
)
from cactus_test_definitions.variable_expressions import (
    Constant,
    Expression,
    NamedVariable,
    NamedVariableType,
    OperationType,
)
from dataclass_wizard.errors import UnknownKeysError


def test_TestProcedureId_synchronised():
    """Ensures that TestProcedureId is in sync with all available TestProcedures YAML files.

    Each MY-TEST.yaml must have a corresponding TestProcedureId.MY_TEST"""

    # Discover all the YAML files
    suffix = ".yaml"
    raw_file_names: set[str] = set()
    for yaml_file in resources.files("cactus_test_definitions.client.procedures").iterdir():
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
    assert all_tps[TestProcedureId.ALL_01] != all_tps[TestProcedureId.ALL_02], "Sanity check on uniqueness"


def test_error_on_duplicate_key():
    """Force test procedures to load and ensure they all validate (and we at least have a few)"""

    with open(Path("tests/data/client/tp_error_duplicate_keys.yaml"), "r") as fp:
        yaml_contents = fp.read()

    with pytest.raises(ValueError):
        parse_test_procedure(yaml_contents)


def test_error_on_extra_key():
    """Force test procedures to load and ensure they all validate (and we at least have a few)"""

    with open(Path("tests/data/client/tp_error_extra_keys.yaml"), "r") as fp:
        yaml_contents = fp.read()

    with pytest.raises(UnknownKeysError):
        parse_test_procedure(yaml_contents)


def test_TestProcedures_action_parameter_types():
    """Tests that lists/dicts/constants/datetimes can all be encoded/decoded via the yaml action definition"""

    with open(Path("tests/data/client/tp_action_parameters.yaml"), "r") as fp:
        tp = parse_test_procedure(fp.read())

    step = tp.steps["Step-1"]
    action = step.actions[0]

    assert action.parameters == {
        "param_list_str": ["List Item 1", "List Item 2", "List Item 3"],
        "param_list_int": [11, 22, 33],
        "param_list_mixed": [
            11,
            2.2,
            "List Item 3",
            datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        ],
        "param_dict_str": {"key1": "value1", "key2": "value2"},
        "param_dict_int": {"key11": 11, "key22": 22},
        "param_int": 11,
        "param_str": "Value 11",
        "param_datetime_utc": datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        "param_datetime_naive": datetime(2025, 1, 2, 3, 4, 5, tzinfo=None),
        "param_with_variable_date": NamedVariable(NamedVariableType.NOW),
        "param_with_variable_db_lookup": NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W),
        "param_with_variable_relative_db_lookup": Expression(
            OperationType.MULTIPLY, Constant(0.25), NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W)
        ),
        "param_with_variable_relative_date": Expression(
            OperationType.SUBTRACT, NamedVariable(NamedVariableType.NOW), Constant(timedelta(minutes=5))
        ),
    }
