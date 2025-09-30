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
ACTION_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    "discovery": {
        "resources": ParameterSchema(True, ParameterType.ListCSIPAusResource),  # What resources to try and resolve?
        "next_polling_window": ParameterSchema(
            False, ParameterType.Boolean
        ),  # If set - delay this until the upcoming polling window (eg- wait for the next whole minute)
    },  # Performs a full discovery / refresh of the client's context from DeviceCapability downwards
    "notifications": {
        "collect": ParameterSchema(
            False, ParameterType.Boolean
        ),  # Collects latest subscription notifications into context
        "disable": ParameterSchema(False, ParameterType.Boolean),  # Simulates HTTP 5XX outage at the endpoint
    },
    "wait": {
        "duration_seconds": ParameterSchema(True, ParameterType.Integer)
    },  # Waits (doing nothing - blocking other step actions) until the specified time period has passed
    "comms-status": {
        "notifications_enabled": ParameterSchema(True, ParameterType.Boolean)  # Enable/Disble notification webhook
    },  # Enables or disables certain communications
    "refresh-resource": {
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # if set - expect 4XX and ErrorPayload
        "expect_rejection_or_empty": ParameterSchema(
            False, ParameterType.Boolean
        ),  # Similar to expect_rejection but also allow en empty list (if it's a list resource)
    },  # Force an existing resource (in the client's context) to be re-fetched via href. Updates context on success
    "insert-end-device": {
        "force_lfdi": ParameterSchema(False, ParameterType.String),  # Forces the use of this LFDI
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # If set - expect 4XX and ErrorPayload
    },  # Inserts an EndDevice and then validates the returned Location header
    "upsert-connection-point": {
        "connectionPointId": ParameterSchema(True, ParameterType.String),
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # If set - expect ErrorPayload reasonCode 1
    },
    "upsert-mup": {
        "mup_id": ParameterSchema(True, ParameterType.String),  # Used to alias the returned MUP ID
        "location": ParameterSchema(True, ParameterType.CSIPAusReadingLocation),
        "reading_types": ParameterSchema(True, ParameterType.ListCSIPAusReadingType),
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # If set - expect 4XX and ErrorPayload
        "mmr_mrids": ParameterSchema(
            False, ParameterType.ListString
        ),  # Must correspond 1-1 with reading_types. Used for forcing specific mrid values
        "pow10_multiplier": ParameterSchema(
            False, ParameterType.Integer
        ),  # Force the use a particular pow10. Defaults to 0 otherwise
    },  # Register a MUP with the specified values. MMR's based on hash of current client / reading types
    "insert-readings": {
        "mup_id": ParameterSchema(True, ParameterType.String),  # Must be previously defined with register-mup
        "values": ParameterSchema(
            True, ParameterType.ReadingTypeValues
        ),  # The sequences of values to send at the MUP post rate
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # If set - expect 4XX and ErrorPayload
    },  # Sends readings - validates that the telemetry is parsed correctly by the server
    "upsert-der-status": {
        "genConnectStatus": ParameterSchema(False, ParameterType.Integer),
        "operationalModeStatus": ParameterSchema(False, ParameterType.Integer),
        "alarmStatus": ParameterSchema(False, ParameterType.Integer),
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # If set - expect 4XX and ErrorPayload
    },  # Sends DERStatus - validates that the server persisted the values correctly
    "upsert-der-capability": {
        "type": ParameterSchema(True, ParameterType.Integer),
        "rtgMaxW": ParameterSchema(True, ParameterType.Integer),
        "modesSupported": ParameterSchema(True, ParameterType.Integer),
        "doeModesSupported": ParameterSchema(True, ParameterType.Integer),
    },  # Sends DERCapability - validates that the server persisted the values correctly
    "upsert-der-settings": {
        "setMaxW": ParameterSchema(True, ParameterType.Integer),
        "setGradW": ParameterSchema(True, ParameterType.Integer),
        "modesEnabled": ParameterSchema(True, ParameterType.Integer),
        "doeModesEnabled": ParameterSchema(True, ParameterType.Integer),
    },  # Sends DERSettings - validates that the server persisted the values correctly
    "send-malformed-der-settings": {
        "updatedTime_missing": ParameterSchema(True, ParameterType.Boolean),  # If true - updatedTime will be stripped
        "modesEnabled_int": ParameterSchema(True, ParameterType.Boolean),  # If true - modesEnabled will send an int
    },  # Sends a malformed DERSettings - expects a failure and that the server will NOT change anything
    "send-malformed-response": {
        "mrid_unknown": ParameterSchema(True, ParameterType.Boolean),  # If true - mrid will be random
        "endDeviceLFDI_unknown": ParameterSchema(True, ParameterType.Boolean),  # If true - endDeviceLfdi will be random
        "response_invalid": ParameterSchema(True, ParameterType.Boolean),  # If true - response will be a reserved value
    },  # Sends a malformed Response (using the most recent DERControl replyTo) - expects a failure response
    "create-subscription": {
        "sub_id": ParameterSchema(True, ParameterType.String),  # Used to alias the returned subscription ID
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
    },  # Sends a new Subscription - validates that the server persisted the values correctly via Location
    "delete-subscription": {
        "sub_id": ParameterSchema(True, ParameterType.String),  # Must match a previously
    },  # Sends a Subscription deletion
    "respond-der-controls": {},  # Enumerates all known DERControls and sends a Response for any that require it
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
