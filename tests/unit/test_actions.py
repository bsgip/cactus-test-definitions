from datetime import datetime, timezone
from decimal import Decimal
from itertools import product
from typing import Any

import pytest
from cactus_test_definitions.actions import (
    Action,
    ActionParameterType,
    is_valid_parameter_type,
    validate_action_parameters,
)
from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.variable_expressions import (
    Constant,
    Expression,
    NamedVariable,
    NamedVariableType,
    OperationType,
)


@pytest.mark.parametrize(
    "value, type",
    product(
        [
            None,
            Expression(OperationType.ADD, Constant(1), Constant(2)),
            Constant(1),
            NamedVariable(NamedVariableType.NOW),
        ],
        list(ActionParameterType),
    ),
)
def test_is_valid_parameter_type_skipped_values(value: Any, type: ActionParameterType):
    """Tests that a number of values aren't considered and always return True"""
    actual = is_valid_parameter_type(type, value)
    assert isinstance(actual, bool)
    assert actual


@pytest.mark.parametrize(
    "type, value, expected",
    [
        (ActionParameterType.Boolean, True, True),
        (ActionParameterType.Boolean, False, True),
        (ActionParameterType.Boolean, 1, False),
        (ActionParameterType.Boolean, [1], False),
        (ActionParameterType.Boolean, "True", False),
        (ActionParameterType.Float, 0, True),
        (ActionParameterType.Float, 0.0, True),
        (ActionParameterType.Float, 1, True),
        (ActionParameterType.Float, 1.1, True),
        (ActionParameterType.Float, Decimal("1.1"), True),
        (ActionParameterType.Float, "1.1", False),
        (ActionParameterType.Float, [1.1], False),
        (ActionParameterType.Integer, 0, True),
        (ActionParameterType.Integer, 0.0, True),
        (ActionParameterType.Integer, 2, True),
        (ActionParameterType.Integer, 2.0, True),
        (ActionParameterType.Integer, Decimal("2.0"), True),
        (ActionParameterType.Integer, Decimal("2.1"), False),
        (ActionParameterType.Integer, 2.1, False),
        (ActionParameterType.Integer, [2], False),
        (ActionParameterType.Integer, "2", False),
        (ActionParameterType.DateTime, datetime(2022, 11, 1, 1, 2, 3), True),
        (ActionParameterType.DateTime, datetime(2022, 11, 1, 1, 2, 3, tzinfo=timezone.utc), True),
        (ActionParameterType.DateTime, "2022-11-01T01:02:03Z", False),
        (ActionParameterType.DateTime, "2022-11-01T01:02:03", False),
        (ActionParameterType.DateTime, 2022, False),
        (ActionParameterType.DateTime, [], False),
        (ActionParameterType.String, "", True),
        (ActionParameterType.String, "abc", True),
        (ActionParameterType.String, "12", True),
        (ActionParameterType.String, 12, False),
        (ActionParameterType.String, ["a"], False),
        (ActionParameterType.ListString, [], True),
        (ActionParameterType.ListString, [""], True),
        (ActionParameterType.ListString, ["", "b"], True),
        (ActionParameterType.ListString, ["", 4, "b"], False),
        (ActionParameterType.ListString, False, False),
        (ActionParameterType.ListString, True, False),
        (ActionParameterType.ListString, 123, False),
    ],
)
def test_is_valid_parameter_type(type: ActionParameterType, value: Any, expected: bool):
    actual = is_valid_parameter_type(type, value)
    assert isinstance(actual, bool)
    assert actual == expected


@pytest.mark.parametrize(
    "action, is_valid",
    [
        (Action("foo", {}), False),
        (Action("enable-listeners", {"listeners": []}), True),
        (Action("enable-listeners", {"listeners": ["other-step"]}), True),
        (Action("enable-listeners", {"listeners": ["other-step"], "unused-param": 123}), False),  # extra param
        (Action("set-default-der-control", {}), True),
        (Action("set-default-der-control", {"opModImpLimW": 12.3, "opModExpLimW": 14}), True),
        (Action("set-default-der-control", {"opModImpLimW": 12.3, "opModExpLimW": "Invalid"}), False),  # bad type
        (Action("create-der-control", {"start": datetime(2022, 1, 3)}), False),  # Missing duration_seconds
        (Action("create-der-control", {"start": datetime(2022, 1, 3), "duration_seconds": 123}), True),
    ],
)
def test_validate_action_parameters(action: Action, is_valid: bool):
    if is_valid:
        validate_action_parameters("foo", "bar", action)
    else:
        with pytest.raises(TestProcedureDefinitionError):
            validate_action_parameters("foo", "bar", action)
