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
class Check:
    """A check represents some validation logic that runs during a Test Step and provides a pass/fail result with a
    description. It will typically inspect the state of the client based on what it has seen from the server

    eg: Ensuring that the client was able to see an EndDevice registration"""

    type: str
    parameters: dict[str, Any]

    def __post_init__(self):
        """Some parameter values might contain variable expressions (eg: a string "$now") that needs to be replaced
        with an parsed Expression object instead."""
        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)


# The parameter schema for each action, keyed by the action name
CHECK_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    "has-discovered": {
        "resources": ParameterSchema(True, ParameterType.ListCSIPAusResource),
        "links": ParameterSchema(True, ParameterType.ListCSIPAusResource),
    },
    "end-device": {
        "matches-client": ParameterSchema(
            False, ParameterType.Boolean
        )  # If set - assert the existence / non existence of an EndDevice for the current client
    },
    "der-control": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},
}
VALID_CHECK_NAMES: set[str] = set(CHECK_PARAMETER_SCHEMA.keys())


def validate_check_parameters(procedure_name: str, check: Check) -> None:
    """Validates the check parameters for the parent TestProcedure based on the CHECK_PARAMETER_SCHEMA

    raises TestProcedureDefinitionError on failure"""
    location = f"{procedure_name} Check: {check.type}"  # Descriptive location of this action being validated

    parameter_schema = CHECK_PARAMETER_SCHEMA.get(check.type, None)
    if parameter_schema is None:
        raise TestProcedureDefinitionError(f"{location} not a valid action name. {VALID_CHECK_NAMES}")

    validate_parameters(location, check.parameters, parameter_schema)
