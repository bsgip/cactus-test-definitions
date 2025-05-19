from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cactus_test_definitions import TestProcedureConfig, TestProcedureDefinitionError
from cactus_test_definitions.variable_expressions import (
    Constant,
    Expression,
    NamedVariable,
    NamedVariableType,
    OperationType,
)


def test_from_yamlfile():
    """This test confirms the standard test procedure yaml file (intended for production use)
    can be read and converted to the appropriate dataclasses.
    """
    test_procedures = TestProcedureConfig.from_resource()
    test_procedures.validate()


@pytest.mark.parametrize(
    "filename",
    [
        # No 'listeners' parameters defined for enable-listeners action (NOT-A-VALID-PARAMETER-NAME supplied instead)
        "tests/data/config_with_errors1.yaml",
        # Action refers to step "NOT-A-VALID-STEP"
        "tests/data/config_with_errors2.yaml",
    ],
)
def test_TestProcedures_validate_raises_exception(filename: str):

    with pytest.raises(TestProcedureDefinitionError):
        _ = TestProcedureConfig.from_yamlfile(path=Path(filename))


def test_TestProcedures_action_parameter_types():
    """Tests that lists/dicts/constants/datetimes can all be encoded/decoded via the yaml action definition"""
    cfg = TestProcedureConfig.from_yamlfile(path=Path("tests/data/config_action_parameters.yaml"), skip_validation=True)
    test_proc = cfg.test_procedures["CUSTOM-01"]
    step = test_proc.steps["Step-1"]
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
