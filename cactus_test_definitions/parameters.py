from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import IntEnum, auto
from typing import Any

from cactus_test_definitions.csipaus import (
    CSIPAusReadingLocation,
    CSIPAusReadingType,
    CSIPAusResource,
)
from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.variable_expressions import is_resolvable_variable


class ParameterType(IntEnum):
    """The various "basic" types that can be set in YAML for a parameter. Rudimentary type checking
    will try to enforce these but they can't be guaranteed"""

    String = auto()
    Integer = auto()
    Float = auto()
    Boolean = auto()
    DateTime = auto()  # TZ aware datetime
    ListString = auto()  # List of strings
    HexBinary = auto()
    CSIPAusResource = auto()  # Member of cactus_test_definitions.csipaus.CSIPAusResource
    ListCSIPAusResource = auto()  # List where each member is a cactus_test_definitions.csipaus.CSIPAusResource
    CSIPAusReadingType = auto()  # Member of cactus_test_definitions.csipaus.CSIPAusReadingType
    ListCSIPAusReadingType = auto()  # List where each member is a cactus_test_definitions.csipaus.CSIPAusReadingType
    CSIPAusReadingLocation = auto()  # Member of cactus_test_definitions.csipaus.CSIPAusReadingLocation
    ReadingTypeValues = auto()  # A dict of type dict[CSIPAusReadingType, list[float]], each list has the same length
    UnsignedInteger = auto()


@dataclass(frozen=True)
class ParameterSchema:
    """What parameters can be passed to a given action/check. Describes a single optional/mandatory field"""

    mandatory: bool  # If this parameter required
    expected_type: ParameterType


def is_valid_parameter_type(expected_type: ParameterType, value: Any) -> bool:
    """Returns true if the specified value "passes" as the expected type. Only performs rudimentary checks to try
    and catch obvious misconfigurations"""
    if value is None:
        return True  # We currently allow None to pass to params. Make it a runtime concern

    if is_resolvable_variable(value):
        return True  # Too hard to validate variable expressions. Make it a runtime concern

    match expected_type:
        case ParameterType.String:
            return isinstance(value, str)
        case ParameterType.Integer:
            if isinstance(value, int):
                return True
            else:
                # Floats/decimals can pass through so long as they have 0 decimal places
                try:
                    return int(value) == value
                except Exception:
                    return False
        case ParameterType.UnsignedInteger:
            # Integer that is greater than or equal to 0
            return is_valid_parameter_type(ParameterType.Integer, value) and value >= 0
        case ParameterType.Float:
            return isinstance(value, float) or isinstance(value, Decimal) or isinstance(value, int)
        case ParameterType.Boolean:
            return isinstance(value, bool)
        case ParameterType.DateTime:
            return isinstance(value, datetime)
        case ParameterType.ListString:
            return isinstance(value, list) and all((isinstance(e, str) for e in value))
        case ParameterType.HexBinary:
            try:
                int(value, 16)
                return True
            except Exception:
                return False
        case ParameterType.CSIPAusResource:
            try:
                return CSIPAusResource(value) == value
            except Exception:
                return False
        case ParameterType.ListCSIPAusResource:
            return isinstance(value, list) and all(
                (is_valid_parameter_type(ParameterType.CSIPAusResource, e) for e in value)
            )
        case ParameterType.CSIPAusReadingType:
            try:
                return CSIPAusReadingType(value) == value
            except Exception:
                return False
        case ParameterType.ListCSIPAusReadingType:
            return isinstance(value, list) and all(
                (is_valid_parameter_type(ParameterType.CSIPAusReadingType, e) for e in value)
            )
        case ParameterType.CSIPAusReadingLocation:
            try:
                return CSIPAusReadingLocation(value) == value
            except Exception:
                return False
        case ParameterType.ReadingTypeValues:
            if not value or not isinstance(value, dict):
                return False

            last_length: int | None = None
            for reading_type, reading_vals in value.items():
                if (
                    not is_valid_parameter_type(ParameterType.CSIPAusReadingType, reading_type)
                    or not isinstance(reading_vals, list)
                    or not all((is_valid_parameter_type(ParameterType.Float, rv) for rv in reading_vals))
                ):
                    return False

                if last_length is None:
                    last_length = len(reading_vals)
                elif last_length != len(reading_vals):
                    return False
            return True

    raise TestProcedureDefinitionError(f"Unexpected ParameterType: {ParameterType}")


def validate_parameters(location: str, parameters: dict[str, Any], valid_schema: dict[str, ParameterSchema]) -> None:
    """Validates parameters against valid_schema for the specified location label.

    location: Label to decorate error messages (eg TestProcedureName.Step.Action)
    parameters: The parameters dict to validate
    valid_schema: The schema to validate parameters against. Keys will be the parameter names, value will be the schema

    raises TestProcedureDefinitionError if parameters is invalid"""

    # Check the supplied parameters match the schema definition
    for param_name, param_value in parameters.items():
        param_schema = valid_schema.get(param_name, None)
        if param_schema is None:
            raise TestProcedureDefinitionError(
                f"{location} doesn't have a parameter {param_name}. Valid params are {set(valid_schema.keys())}"
            )

        # Check the type
        if not is_valid_parameter_type(param_schema.expected_type, param_value):
            raise TestProcedureDefinitionError(
                f"{location} has parameter {param_name} expecting {param_schema.expected_type} but got {param_value}"
            )

    # Check all mandatory parameters are set
    for param_name, param_schema in valid_schema.items():
        if param_schema.mandatory and param_name not in parameters:
            raise TestProcedureDefinitionError(f"{location} is missing mandatory parameter {param_name}")
