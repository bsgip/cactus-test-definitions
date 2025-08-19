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
    """A check represents some validation logic that runs during test finalization and can provide a pass/fail
    status beyond the "basic" flow of a test procedure. Checks will typically inspect the database/history of requests
    ino order to determine compliance.

    eg: Looking through past requests to an endpoint to validate it was called at a specific rate"""

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
    "all-steps-complete": {"ignored_steps": ParameterSchema(False, ParameterType.ListString)},
    "all-notifications-transmitted": {},
    "end-device-contents": {
        "has_connection_point_id": ParameterSchema(False, ParameterType.Boolean),
        "deviceCategory_anyset": ParameterSchema(False, ParameterType.HexBinary),  # Any of these bits set to 1
    },
    "der-settings-contents": {
        "setGradW": ParameterSchema(False, ParameterType.Integer),  # Hundredths of a percent / second
        "doeModesEnabled": ParameterSchema(False, ParameterType.Boolean),  # Is ANY value set?
        "doeModesEnabled_set": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to one
        "doeModesEnabled_unset": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to zero
        "modesEnabled_set": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to one
        "modesEnabled_unset": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to zero
        "vppModesEnabled_set": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to one
        "vppModesEnabled_unset": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to zero
        "setMaxVA": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
        "setMaxVar": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
        "setMaxW": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
        "setMaxChargeRateW": ParameterSchema(False, ParameterType.Boolean),
        "setMaxDischargeRateW": ParameterSchema(False, ParameterType.Boolean),
        "setMaxWh": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
        "setMinWh": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
    },
    "der-capability-contents": {
        "doeModesSupported": ParameterSchema(False, ParameterType.Boolean),  # Minimum bits set to one
        "doeModesSupported_set": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to one
        "doeModesSupported_unset": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to zero
        "modesSupported_set": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to one
        "modesSupported_unset": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to zero
        "vppModesSupported_set": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to one
        "vppModesSupported_unset": ParameterSchema(False, ParameterType.HexBinary),  # Minimum bits set to zero
        "rtgMaxVA": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
        "rtgMaxVar": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
        "rtgMaxW": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
        "rtgMaxChargeRateW": ParameterSchema(
            False, ParameterType.Boolean
        ),  # Expected expression that evaluates to boolean
        "rtgMaxDischargeRateW": ParameterSchema(
            False, ParameterType.Boolean
        ),  # Expected expression that evaluates to boolean
        "rtgMaxWh": ParameterSchema(False, ParameterType.Boolean),  # Expected expression that evaluates to boolean
    },
    "der-status-contents": {
        "genConnectStatus": ParameterSchema(False, ParameterType.Integer),
        "genConnectStatus_bit0": ParameterSchema(False, ParameterType.Boolean),
        "genConnectStatus_bit1": ParameterSchema(False, ParameterType.Boolean),
        "genConnectStatus_bit2": ParameterSchema(False, ParameterType.Boolean),
        "operationalModeStatus": ParameterSchema(False, ParameterType.Integer),
        "alarmStatus": ParameterSchema(False, ParameterType.Integer),
    },
    "readings-site-active-power": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},
    "readings-site-reactive-power": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},
    "readings-site-voltage": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},
    "readings-der-active-power": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},
    "readings-der-reactive-power": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},
    "readings-der-voltage": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},
    "readings-der-stored-energy": {"minimum_count": ParameterSchema(True, ParameterType.Integer)},  # Storage extension
    "subscription-contents": {"subscribed_resource": ParameterSchema(True, ParameterType.String)},
    "response-contents": {
        "latest": ParameterSchema(False, ParameterType.Boolean),
        "status": ParameterSchema(False, ParameterType.Integer),
        "all": ParameterSchema(False, ParameterType.Boolean),
    },
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
