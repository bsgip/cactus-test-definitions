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
    parameters: dict[str, Any]

    def __post_init__(self):
        """Some parameter values might contain variable expressions (eg: a string "$now") that needs to be replaced
        with an parsed Expression object instead."""
        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)


# The parameter schema for each action, keyed by the action name
ACTION_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    "enable-steps": {"steps": ParameterSchema(True, ParameterType.ListString)},
    "remove-steps": {"steps": ParameterSchema(True, ParameterType.ListString)},
    "finish-test": {},
    "set-default-der-control": {
        "derp_id": ParameterSchema(False, ParameterType.Integer),
        "opModImpLimW": ParameterSchema(False, ParameterType.Float),
        "opModExpLimW": ParameterSchema(False, ParameterType.Float),
        "opModGenLimW": ParameterSchema(False, ParameterType.Float),
        "opModLoadLimW": ParameterSchema(False, ParameterType.Float),
        "opModStorageTargetW": ParameterSchema(False, ParameterType.Float),
        "setGradW": ParameterSchema(False, ParameterType.Integer),  # Hundredths of a percent / second
        "cancelled": ParameterSchema(False, ParameterType.Boolean),
    },
    "create-der-control": {
        "start": ParameterSchema(True, ParameterType.DateTime),
        "duration_seconds": ParameterSchema(True, ParameterType.Integer),
        "pow_10_multipliers": ParameterSchema(False, ParameterType.Integer),
        "primacy": ParameterSchema(False, ParameterType.Integer),
        "fsa_id": ParameterSchema(False, ParameterType.Integer),
        "randomizeStart_seconds": ParameterSchema(False, ParameterType.Integer),
        "ramp_time_seconds": ParameterSchema(False, ParameterType.Float),
        "opModEnergize": ParameterSchema(False, ParameterType.Boolean),
        "opModConnect": ParameterSchema(False, ParameterType.Boolean),
        "opModImpLimW": ParameterSchema(False, ParameterType.Float),
        "opModExpLimW": ParameterSchema(False, ParameterType.Float),
        "opModGenLimW": ParameterSchema(False, ParameterType.Float),
        "opModLoadLimW": ParameterSchema(False, ParameterType.Float),
        "opModFixedW": ParameterSchema(False, ParameterType.Float),
        "opModStorageTargetW": ParameterSchema(False, ParameterType.Float),
        "tag": ParameterSchema(False, ParameterType.String),
    },
    "create-der-program": {
        "primacy": ParameterSchema(True, ParameterType.Integer),
        "fsa_id": ParameterSchema(False, ParameterType.Integer),
    },
    "cancel-active-der-controls": {},
    "set-comms-rate": {
        "dcap_poll_seconds": ParameterSchema(False, ParameterType.Integer),
        "edev_post_seconds": ParameterSchema(False, ParameterType.Integer),
        "edev_list_poll_seconds": ParameterSchema(False, ParameterType.Integer),
        "fsa_list_poll_seconds": ParameterSchema(False, ParameterType.Integer),
        "derp_list_poll_seconds": ParameterSchema(False, ParameterType.Integer),
        "der_list_poll_seconds": ParameterSchema(False, ParameterType.Integer),
        "mup_post_seconds": ParameterSchema(False, ParameterType.Integer),
    },
    "communications-status": {"enabled": ParameterSchema(True, ParameterType.Boolean)},
    "edev-registration-links": {"enabled": ParameterSchema(True, ParameterType.Boolean)},
    "register-end-device": {
        "nmi": ParameterSchema(False, ParameterType.String),
        "registration_pin": ParameterSchema(False, ParameterType.Integer),
        "aggregator_lfdi": ParameterSchema(False, ParameterType.HexBinary),
        "aggregator_sfdi": ParameterSchema(False, ParameterType.Integer),
    },
}
VALID_ACTION_NAMES: set[str] = set(ACTION_PARAMETER_SCHEMA.keys())


def validate_action_parameters(procedure_name: str, step: str, action: Action) -> None:
    """Validates the action parameters for the parent TestProcedure based on the  ACTION_PARAMETER_SCHEMA

    raises TestProcedureDefinitionError on failure"""
    location = f"{procedure_name}.{step} Action: {action.type}"  # Descriptive location of this action being validated

    parameter_schema = ACTION_PARAMETER_SCHEMA.get(action.type, None)
    if parameter_schema is None:
        raise TestProcedureDefinitionError(f"{location} not a valid action name. {VALID_ACTION_NAMES}")

    validate_parameters(location, action.parameters, parameter_schema)
