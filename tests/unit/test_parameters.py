from datetime import datetime, timezone
from decimal import Decimal
from itertools import product
from typing import Any

import pytest
from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.parameters import (
    ParameterSchema,
    ParameterType,
    is_valid_parameter_type,
    validate_parameters,
)
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
        list(ParameterType),
    ),
)
def test_is_valid_parameter_type_skipped_values(value: Any, type: ParameterType):
    """Tests that a number of values aren't considered and always return True"""
    actual = is_valid_parameter_type(type, value)
    assert isinstance(actual, bool)
    assert actual


@pytest.mark.parametrize(
    "type, value, expected",
    [
        (ParameterType.Boolean, True, True),
        (ParameterType.Boolean, False, True),
        (ParameterType.Boolean, 1, False),
        (ParameterType.Boolean, [1], False),
        (ParameterType.Boolean, "True", False),
        (ParameterType.Float, 0, True),
        (ParameterType.Float, 0.0, True),
        (ParameterType.Float, 1, True),
        (ParameterType.Float, 1.1, True),
        (ParameterType.Float, Decimal("1.1"), True),
        (ParameterType.Float, "1.1", False),
        (ParameterType.Float, [1.1], False),
        (ParameterType.Integer, 0, True),
        (ParameterType.Integer, 0.0, True),
        (ParameterType.Integer, 2, True),
        (ParameterType.Integer, 2.0, True),
        (ParameterType.Integer, Decimal("2.0"), True),
        (ParameterType.Integer, Decimal("2.1"), False),
        (ParameterType.Integer, 2.1, False),
        (ParameterType.Integer, [2], False),
        (ParameterType.Integer, "2", False),
        (ParameterType.DateTime, datetime(2022, 11, 1, 1, 2, 3), True),
        (ParameterType.DateTime, datetime(2022, 11, 1, 1, 2, 3, tzinfo=timezone.utc), True),
        (ParameterType.DateTime, "2022-11-01T01:02:03Z", False),
        (ParameterType.DateTime, "2022-11-01T01:02:03", False),
        (ParameterType.DateTime, 2022, False),
        (ParameterType.DateTime, [], False),
        (ParameterType.String, "", True),
        (ParameterType.String, "abc", True),
        (ParameterType.String, "12", True),
        (ParameterType.String, 12, False),
        (ParameterType.String, ["a"], False),
        (ParameterType.ListString, [], True),
        (ParameterType.ListString, [""], True),
        (ParameterType.ListString, ["", "b"], True),
        (ParameterType.ListString, ["", 4, "b"], False),
        (ParameterType.ListString, False, False),
        (ParameterType.ListString, True, False),
        (ParameterType.ListString, 123, False),
        (ParameterType.HexBinary, "AB", True),
        (ParameterType.HexBinary, "XY", False),
        (ParameterType.HexBinary, 12, False),
        (ParameterType.HexBinary, ["AB"], False),
        (ParameterType.HexBinary, 0.0, False),
        (ParameterType.HexBinary, [12], False),
        (ParameterType.HexBinary, 1.2, False),
        (ParameterType.HexBinary, Decimal("1.0"), False),
        (ParameterType.HexBinary, True, False),
        (ParameterType.CSIPAusResource, True, False),
        (ParameterType.CSIPAusResource, 123, False),
        (ParameterType.CSIPAusResource, "NotAResourceType", False),
        (ParameterType.CSIPAusResource, "ActivePowerInstantaneous", False),
        (ParameterType.CSIPAusResource, "EndDevice", True),
        (ParameterType.CSIPAusResource, ["EndDevice"], False),
        (ParameterType.ListCSIPAusResource, True, False),
        (ParameterType.ListCSIPAusResource, 123, False),
        (ParameterType.ListCSIPAusResource, "NotAResourceType", False),
        (ParameterType.ListCSIPAusResource, "EndDevice", False),
        (ParameterType.ListCSIPAusResource, ["EndDevice"], True),
        (ParameterType.ListCSIPAusResource, ["EndDevice", "NotAResource"], False),
        (ParameterType.ListCSIPAusResource, ["ActivePowerInstantaneous"], False),
        (ParameterType.CSIPAusReadingType, True, False),
        (ParameterType.CSIPAusReadingType, 123, False),
        (ParameterType.CSIPAusReadingType, "NotAResourceType", False),
        (ParameterType.CSIPAusReadingType, "EndDevice", False),
        (ParameterType.CSIPAusReadingType, "ActivePowerInstantaneous", True),
        (ParameterType.CSIPAusReadingType, ["ActivePowerSiteInstantaneous"], False),
        (ParameterType.ListCSIPAusReadingType, True, False),
        (ParameterType.ListCSIPAusReadingType, 123, False),
        (ParameterType.ListCSIPAusReadingType, "NotAResourceType", False),
        (ParameterType.ListCSIPAusReadingType, "EndDevice", False),
        (ParameterType.ListCSIPAusReadingType, "ActivePowerInstantaneous", False),
        (ParameterType.ListCSIPAusReadingType, ["ActivePowerInstantaneous"], True),
        (ParameterType.ListCSIPAusReadingType, ["ActivePowerInstantaneous", "NotAResource"], False),
        (ParameterType.ListCSIPAusReadingType, ["EndDevice"], False),
        (ParameterType.CSIPAusReadingLocation, True, False),
        (ParameterType.CSIPAusReadingLocation, 123, False),
        (ParameterType.CSIPAusReadingLocation, "NotAResourceType", False),
        (ParameterType.CSIPAusReadingLocation, "EndDevice", False),
        (ParameterType.CSIPAusReadingLocation, "Site", True),
        (ParameterType.CSIPAusReadingLocation, ["Site"], False),
        (ParameterType.ReadingTypeValues, 123, False),
        (ParameterType.ReadingTypeValues, "ActivePowerInstantaneous", False),
        (ParameterType.ReadingTypeValues, [123], False),
        (ParameterType.ReadingTypeValues, {}, False),
        (
            ParameterType.ReadingTypeValues,
            {"ActivePowerInstantaneous": [100, 1.23], "ActivePowerAverage": [200, -300]},
            True,
        ),
        (
            ParameterType.ReadingTypeValues,
            {"ActivePowerInstantaneous": [100, 200], "ActivePowerAverage": [200, 300, 400]},
            False,
        ),
        (
            ParameterType.ReadingTypeValues,
            {"ActivePowerInstantaneous": [100, 200], "ActivePowerAverage": [200, 300], "Foo": [100, 200]},
            False,
        ),
        (
            ParameterType.ReadingTypeValues,
            {"ActivePowerInstantaneous": [100, 200], "ActivePowerAverage": [200, "1.23"]},
            False,
        ),
        (
            ParameterType.ReadingTypeValues,
            {"ActivePowerInstantaneous": 100, "ActivePowerAverage": 200},
            False,
        ),
    ],
)
def test_is_valid_parameter_type(type: ParameterType, value: Any, expected: bool):
    actual = is_valid_parameter_type(type, value)
    assert isinstance(actual, bool)
    assert actual == expected


@pytest.mark.parametrize(
    "parameters, schema, is_valid",
    [
        ({}, {}, True),
        ({"foo": 1}, {}, False),
        ({"foo": 1}, {"foo": ParameterSchema(True, ParameterType.Integer)}, True),
        ({"foo": 1}, {"foo": ParameterSchema(True, ParameterType.Float)}, True),
        ({"foo": 1}, {"foo": ParameterSchema(True, ParameterType.String)}, False),  # wrong type
        (
            {"foo": 1},
            {"foo": ParameterSchema(True, ParameterType.Integer), "bar": ParameterSchema(False, ParameterType.String)},
            True,
        ),  # Optional param is OK to miss
        (
            {"foo": 1},
            {"foo": ParameterSchema(True, ParameterType.Integer), "bar": ParameterSchema(True, ParameterType.String)},
            False,
        ),  # Missing mandatory param
        (
            {"foo": None, "bar": "2", "baz": 4},
            {
                "foo": ParameterSchema(True, ParameterType.Integer),
                "bar": ParameterSchema(True, ParameterType.String),
                "baz": ParameterSchema(False, ParameterType.Float),
            },
            True,
        ),
    ],
)
def test_validate_action_parameters(parameters: dict, schema: dict, is_valid: bool):
    if is_valid:
        validate_parameters("foo", parameters, schema)
    else:
        with pytest.raises(TestProcedureDefinitionError):
            validate_parameters("foo", parameters, schema)
