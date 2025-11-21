from dataclasses import dataclass
from typing import Any

from cactus_test_definitions.client.checks import Check
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
class Event:
    """An event represents some form of client/other criteria occurring (trigger). When an event trigger is met,
    any associated actions with the parent Step will be run.

    Events can have checks that must be all returned True/Pass at the moment the event is triggered otherwise
    the event trigger will be ignored."""

    type: str  # The type of event being listened for
    parameters: dict[str, Any]  # Any parameters to the event listener
    checks: list[Check] | None = None  # This event will be blocked from triggering if any of these checks return False

    def __post_init__(self):
        """Some parameter values might contain variable expressions (eg: a string "$now") that needs to be replaced
        with an parsed Expression object instead."""
        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)


# The parameter schema for each event, keyed by the event name
EVENT_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    "GET-request-received": {
        "endpoint": ParameterSchema(True, ParameterType.String),
        "serve_request_first": ParameterSchema(False, ParameterType.Boolean),
    },
    "POST-request-received": {
        "endpoint": ParameterSchema(True, ParameterType.String),
        "serve_request_first": ParameterSchema(False, ParameterType.Boolean),
    },
    "PUT-request-received": {
        "endpoint": ParameterSchema(True, ParameterType.String),
        "serve_request_first": ParameterSchema(False, ParameterType.Boolean),
    },
    "DELETE-request-received": {
        "endpoint": ParameterSchema(True, ParameterType.String),
        "serve_request_first": ParameterSchema(False, ParameterType.Boolean),
    },
    "wait": {"duration_seconds": ParameterSchema(True, ParameterType.Integer)},
}
VALID_EVENT_NAMES: set[str] = set(EVENT_PARAMETER_SCHEMA.keys())


def validate_event_parameters(procedure_name: str, step: str, event: Event) -> None:
    """Validates the event parameters for the parent TestProcedure based on the  EVENT_PARAMETER_SCHEMA

    raises TestProcedureDefinitionError on failure"""
    location = f"{procedure_name}.{step} Event: {event.type}"  # Descriptive location of this event being validated

    parameter_schema = EVENT_PARAMETER_SCHEMA.get(event.type, None)
    if parameter_schema is None:
        raise TestProcedureDefinitionError(f"{location} not a valid event name. {VALID_EVENT_NAMES}")

    validate_parameters(location, event.parameters, parameter_schema)
