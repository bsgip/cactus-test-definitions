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
    parameters: dict[str, Any] = None  # type: ignore # This will be forced in __post_init__

    def __post_init__(self):
        """Some parameter values might contain variable expressions (eg: a string "$now") that needs to be replaced
        with an parsed Expression object instead."""
        if self.parameters is None:
            self.parameters = {}
        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)


# The parameter schema for each action, keyed by the action name
CHECK_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    "discovered": {
        "resources": ParameterSchema(False, ParameterType.ListCSIPAusResource),
        "links": ParameterSchema(False, ParameterType.ListCSIPAusResource),
    },
    "time-synced": {},  # Passes if the current Time resource is synced with this client's date/time
    "function-set-assignment": {
        "minimum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at least this many FSAs to pass
        "maximum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at most this many FSAs to pass
        "matches_client_edev": ParameterSchema(
            False, ParameterType.Boolean
        ),  # If True - only FSAs assigned to the client's EndDevice will be counted
        "sub_id": ParameterSchema(
            False, ParameterType.String
        ),  # If set - only FSAs received via this subscription will be counted
    },
    "end-device-list": {
        "minimum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at least this many edev lists to pass
        "maximum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at most this many edev lists to pass
        "poll_rate": ParameterSchema(
            False, ParameterType.Integer
        ),  # If set - will only count an EndDeviceList with this exact pollRate
        "sub_id": ParameterSchema(
            False, ParameterType.String
        ),  # If set - only EndDeviceLists received via this subscription will be counted
    },
    "end-device": {
        "matches_client": ParameterSchema(
            True, ParameterType.Boolean
        ),  # assert the existence / non existence of an EndDevice for the current client
        "matches_pin": ParameterSchema(
            False, ParameterType.Boolean
        ),  # if set - The matches_client criteria will ALSO check the registration PIN for the EndDevice. Default False
    },
    "der-program": {
        "minimum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at least this many derps to pass
        "maximum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at most this many derps to pass
        "primacy": ParameterSchema(False, ParameterType.Integer),  # Filters derps based on this primacy value
        "fsa_index": ParameterSchema(
            False, ParameterType.Integer
        ),  # Filters derps that belong to the nth (0 based) FunctionSetAssignment index
        "sub_id": ParameterSchema(
            False, ParameterType.String
        ),  # Filters derps to only those received via this named subscription
    },
    "der-control": {
        "minimum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at least this many controls to pass
        "maximum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at most this many controls to pass
        "latest": ParameterSchema(False, ParameterType.Boolean),  # forces filter checks against the most recent control
        "opModImpLimW": ParameterSchema(False, ParameterType.Float),  # Filters controls based on this value
        "opModExpLimW": ParameterSchema(False, ParameterType.Float),  # Filters controls based on this value
        "opModLoadLimW": ParameterSchema(False, ParameterType.Float),  # Filters controls based on this value
        "opModGenLimW": ParameterSchema(False, ParameterType.Float),  # Filters controls based on this value
        "opModEnergize": ParameterSchema(False, ParameterType.Boolean),  # Filters controls based on this value
        "opModConnect": ParameterSchema(False, ParameterType.Boolean),  # Filters controls based on this value
        "opModFixedW": ParameterSchema(False, ParameterType.Float),  # Filters controls based on this value
        "rampTms": ParameterSchema(False, ParameterType.Integer),  # Filter on this val. 0 means negative assertion
        "randomizeStart": ParameterSchema(False, ParameterType.Integer),  # Filter on this val (in seconds)
        "event_status": ParameterSchema(False, ParameterType.Integer),  # Filter on Event.status value
        "responseRequired": ParameterSchema(False, ParameterType.Integer),  # Filter on responseRequired value
        "derp_primacy": ParameterSchema(
            False, ParameterType.Integer
        ),  # Filter to control's belonging to a DERProgram with this primacy value
        "sub_id": ParameterSchema(
            False, ParameterType.String
        ),  # Filters control to only those received via this named subscription
        "duration": ParameterSchema(False, ParameterType.Integer),  # Filter on duration value
    },  # Matches many DERControls (specified by minimum_count) against additional other filter criteria
    "default-der-control": {
        "minimum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at least this many default der controls
        "maximum_count": ParameterSchema(False, ParameterType.Integer),  # Needs at most this many default der controls
        "opModImpLimW": ParameterSchema(False, ParameterType.Float),
        "opModExpLimW": ParameterSchema(False, ParameterType.Float),
        "opModGenLimW": ParameterSchema(False, ParameterType.Float),
        "opModLoadLimW": ParameterSchema(False, ParameterType.Float),
        "setGradW": ParameterSchema(False, ParameterType.Integer),  # Hundredths of a percent / second
        "sub_id": ParameterSchema(
            False, ParameterType.String
        ),  # Filters default control to only those received via this named subscription
        "derp_primacy": ParameterSchema(
            False, ParameterType.Integer
        ),  # Filter to control's belonging to a DERProgram with this primacy value
    },  # matches any DefaultDERControl with the specified values
    "mirror-usage-point": {
        "matches": ParameterSchema(True, ParameterType.Boolean),  # True for positive assert, False for negative assert
        "location": ParameterSchema(False, ParameterType.CSIPAusReadingLocation),  # If not specified - match anything
        "reading_types": ParameterSchema(False, ParameterType.ListCSIPAusReadingType),  # If not specified - match all
        "mmr_mrids": ParameterSchema(
            False, ParameterType.ListString
        ),  # Must correspond 1-1 with reading_types. Used for forcing specific mrid values
        "post_rate_seconds": ParameterSchema(False, ParameterType.Integer),  # Only asserted if specified
    },  # True if the matches assertion finds a MirrorUsagePoint with the specified parameters (requires exact match)
    "subscription": {
        "matches": ParameterSchema(True, ParameterType.Boolean),  # True for positive assert, False for negative assert
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
    },  # Matches the existence/nonexistence of a subscription for the specified resource
    "poll-rate": {
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
        "poll_rate_seconds": ParameterSchema(True, ParameterType.Integer),
    },  # Asserts a specific poll rate value
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
