from dataclasses import dataclass
from typing import Any

from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.parameters import (
    ParameterSchema,
    ParameterType,
    validate_parameters,
)
from cactus_test_definitions.variable_expressions import (
    parse_variable_expression_body,
    try_extract_variable_expression,
)


@dataclass
class Action:
    type: str
    client: str | None = None  # use the client with this id to execute this action. If None, use the 0th client
    parameters: dict[str, Any] | None = None

    def __post_init__(self):
        """Some parameter values might contain variable expressions (eg: a string "$now") that needs to be replaced
        with an parsed Expression object instead."""
        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)


# The parameter schema for each action, keyed by the action name
ACTION_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    "discovery": {
        "wait_for_resource_links": ParameterSchema(False, ParameterType.ListCSIPAusResource),
        "wait_for_resources": ParameterSchema(False, ParameterType.ListCSIPAusResource),
    },
    "register-end-device": {
        "resolve_location_header": ParameterSchema(False, ParameterType.Boolean),  # If set - follow the Location header
        "expect_rejection": ParameterSchema(False, ParameterType.String),  # If set - expect 4XX and ErrorPayload
    },
    "register-connection-point": {
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # If set - expect ErrorPayload reasonCode 1
    },
    "register-mup": {
        "mup_id": ParameterSchema(True, ParameterType.String),  # Used to alias the returned MUP ID
        "location": ParameterSchema(True, ParameterType.CSIPAusReadingLocation),
        "reading_types": ParameterSchema(False, ParameterType.ListCSIPAusReadingType),
    },
    "schedule-readings": {
        "mup_id": ParameterSchema(True, ParameterType.String),  # Must be previously defined with register-mup
        "values": ParameterSchema(True, ParameterType.ReadingTypeValues),
    },
}
VALID_ACTION_NAMES: set[str] = set(ACTION_PARAMETER_SCHEMA.keys())


def validate_action_parameters(procedure_name: str, step_name: int, action: Action) -> None:
    """Validates the action parameters for the parent TestProcedure based on the  ACTION_PARAMETER_SCHEMA

    raises TestProcedureDefinitionError on failure"""
    location = f"{procedure_name}.step[{step_name}]"  # Descriptive location

    parameter_schema = ACTION_PARAMETER_SCHEMA.get(action.type, None)
    if parameter_schema is None:
        raise TestProcedureDefinitionError(
            f"{location} has an invalid action name '{action.type}'. Valid Names: {VALID_ACTION_NAMES}"
        )

    validate_parameters(location, action.parameters, parameter_schema)
