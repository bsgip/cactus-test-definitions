from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import IntEnum, auto
from typing import Any

from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.variable_expressions import (
    is_resolvable_variable,
    parse_variable_expression_body,
    try_extract_variable_expression,
)


@dataclass
class Action:
    type: str
    parameters: dict[str, Any]

    def __post_init__(self):
        """Some parameter values might contain variable expressions (eg: a string "$now") that needs to be replaced
        with an parsed Expression object instead."""
        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr)


class ActionParameterType(IntEnum):
    """The various "basic" types that can be set in YAML for an Action's parameter. Rudimentary type checking
    will try to enforce these but they can't be guaranteed"""

    String = auto()
    Integer = auto()
    Float = auto()
    Boolean = auto()
    DateTime = auto()  # TZ aware datetime
    ListString = auto()  # List of strings


@dataclass(frozen=True)
class ActionParameterSchema:
    """What parameters can be passed to a given action. Describes a single optional/mandatory field"""

    mandatory: bool  # If this parameter required
    expected_type: ActionParameterType


# The parameter schema for each action, keyed by the action name
ACTION_PARAMETER_SCHEMA: dict[str, dict[str, ActionParameterSchema]] = {
    "enable-listeners": {"listeners": ActionParameterSchema(True, ActionParameterType.ListString)},
    "remove-listeners": {"listeners": ActionParameterSchema(True, ActionParameterType.ListString)},
    "set-default-der-control": {
        "opModImpLimW": ActionParameterSchema(False, ActionParameterType.Float),
        "opModExpLimW": ActionParameterSchema(False, ActionParameterType.Float),
        "opModGenLimW": ActionParameterSchema(False, ActionParameterType.Float),
        "opModLoadLimW": ActionParameterSchema(False, ActionParameterType.Float),
        "setGradW": ActionParameterSchema(False, ActionParameterType.Float),
    },
    "create-der-control": {
        "start": ActionParameterSchema(True, ActionParameterType.DateTime),
        "duration_seconds": ActionParameterSchema(True, ActionParameterType.Integer),
        "pow_10_multipliers": ActionParameterSchema(False, ActionParameterType.Integer),
        "primacy": ActionParameterSchema(False, ActionParameterType.Integer),
        "randomizeStart_seconds": ActionParameterSchema(False, ActionParameterType.Integer),
        "opModEnergize": ActionParameterSchema(False, ActionParameterType.Boolean),
        "opModConnect": ActionParameterSchema(False, ActionParameterType.Boolean),
        "opModImpLimW": ActionParameterSchema(False, ActionParameterType.Float),
        "opModExpLimW": ActionParameterSchema(False, ActionParameterType.Float),
        "opModGenLimW": ActionParameterSchema(False, ActionParameterType.Float),
        "opModLoadLimW": ActionParameterSchema(False, ActionParameterType.Float),
    },
    "cancel-active-der-controls": {},
    "set-poll-rate": {
        "rate_seconds": ActionParameterSchema(True, ActionParameterType.Integer),
    },
    "set-post-rate": {
        "rate_seconds": ActionParameterSchema(True, ActionParameterType.Integer),
    },
    "communications-loss": {},
    "communications-restore": {},
}
VALID_ACTION_NAMES: set[str] = set(ACTION_PARAMETER_SCHEMA.keys())


def is_valid_parameter_type(expected_type: ActionParameterType, value: Any) -> bool:
    """Returns true if the specified value "passes" as the expected type. Only performs rudimentary checks to try
    and catch obvious misconfigurations"""
    if value is None:
        return True  # We currently allow None to pass to params. Make it a runtime concern

    if is_resolvable_variable(value):
        return True  # Too hard to validate variable expressions. Make it a runtime concern

    match (expected_type):
        case ActionParameterType.String:
            return isinstance(value, str)
        case ActionParameterType.Integer:
            if isinstance(value, int):
                return True
            else:
                # Floats/decimals can pass through so long as they have 0 decimal places
                try:
                    return int(value) == value
                except Exception:
                    return False
        case ActionParameterType.Float:
            return isinstance(value, float) or isinstance(value, Decimal) or isinstance(value, int)
        case ActionParameterType.Boolean:
            return isinstance(value, bool)
        case ActionParameterType.DateTime:
            return isinstance(value, datetime)
        case ActionParameterType.ListString:
            return isinstance(value, list) and all((isinstance(e, str) for e in value))

    raise TestProcedureDefinitionError(f"Unexpected ActionParameterType: {ActionParameterType}")


def validate_action_parameters(procedure_name: str, step: str, action: Action) -> None:
    """Validates the action parameters for the parent TestProcedure based on the  ACTION_PARAMETER_SCHEMA

    raises TestProcedureDefinitionError on failure"""
    loc = f"{procedure_name}.{step} Action: {action.type}"  # Descriptive location of this action being validated

    all_param_schema = ACTION_PARAMETER_SCHEMA.get(action.type, None)
    if all_param_schema is None:
        raise TestProcedureDefinitionError(f"{loc} not a valid action name. {VALID_ACTION_NAMES}")

    # Check the supplied parameters match the schema definition
    for param_name, param_value in action.parameters.items():
        schema = all_param_schema.get(param_name, None)
        if schema is None:
            raise TestProcedureDefinitionError(
                f"{loc} doesn't have a parameter {param_name}. Valid params are {set(all_param_schema.keys())}"
            )

        # Check the type - we ignore variables as that is tricky to properly type check
        if not is_valid_parameter_type(schema.expected_type, param_value):
            raise TestProcedureDefinitionError(
                f"{loc} has parameter {param_name} expecting {schema.expected_type} but got {param_value}"
            )

    # Check all mandatory parameters are set
    for param_name, schema in all_param_schema.items():
        if schema.mandatory and param_name not in action.parameters:
            raise TestProcedureDefinitionError(f"{loc} is missing mandatory parameter {param_name}")
