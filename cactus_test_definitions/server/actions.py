from dataclasses import dataclass
from typing import Any, ClassVar

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

    RESERVED_NAMES: ClassVar[tuple[str, ...]] = (
        "admin-setup",
        "admin-teardown",
    )  # type names that test definitions shouldn't be able to redefine

    def __post_init__(self):
        """Some parameter values might contain variable expressions (eg: a string "$now") that needs to be replaced
        with an parsed Expression object instead."""
        if self.parameters is None:
            self.parameters = {}

        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)

    @staticmethod
    def admin_setup() -> "Action":
        """Creates common setup action not defineable from test procedure."""
        return Action(type="admin-setup", client="NOT_APPLICABLE")

    @staticmethod
    def admin_teardown() -> "Action":
        """Creates common teardown action not defineable from test procedure."""
        return Action(type="admin-teardown", client="NOT_APPLICABLE")


# The parameter schema for each action, keyed by the action name
ACTION_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    "admin-device-register": {},  # Admin api plugin specific to out of band register
    "discovery": {
        "resources": ParameterSchema(True, ParameterType.ListCSIPAusResource),  # What resources to try and resolve?
        "next_polling_window": ParameterSchema(
            False, ParameterType.Boolean
        ),  # If set - delay this until the upcoming polling window (eg- wait for the next whole minute)
        "list_limit": ParameterSchema(False, ParameterType.Integer),
    },  # Performs a full discovery / refresh of the client's context from DeviceCapability downwards
    "notifications": {
        "sub_id": ParameterSchema(True, ParameterType.String),  # Must match a previously created subscription
        "collect": ParameterSchema(
            False, ParameterType.Boolean
        ),  # Collects latest subscription notifications into context
        "disable": ParameterSchema(False, ParameterType.Boolean),  # Simulates HTTP 5XX outage at the endpoint
    },
    "wait": {
        "duration_seconds": ParameterSchema(True, ParameterType.Integer)
    },  # Waits (doing nothing - blocking other step actions) until the specified time period has passed
    "refresh-resource": {
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
        "expect_rejection": ParameterSchema(False, ParameterType.Boolean),  # True - expect 4XX and ErrorPayload.
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
        ),  # Must correspond 1-1 with reading_types. Used for forcing specific mrid values (must be 32 hex chars)
        "pow10_multiplier": ParameterSchema(
            False, ParameterType.Integer
        ),  # Force the use a particular pow10. Defaults to 0 otherwise
        "set_mup_mrid": ParameterSchema(False, ParameterType.String),  # If set, forces mup mrid identity
    },  # Register a MUP with the specified values. MMR's based on hash of current client / reading types
    "insert-readings": {
        "mup_id": ParameterSchema(True, ParameterType.String),  # Must be previously defined with register-mup
        "values": ParameterSchema(
            True, ParameterType.ReadingTypeValues
        ),  # The sequences of values to send at the MUP post rate
        "mmr_mrids": ParameterSchema(
            False, ParameterType.ListString
        ),  # Must correspond 1-1 with values. Used for forcing specific mrid values
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
    "forget": {
        "resources": ParameterSchema(True, ParameterType.ListCSIPAusResource),  # What resources to forget?
    },  # Forces the removal/forgetting of a client's store for the specified resource types
    "simulate-client": {
        "frequency_seconds": ParameterSchema(True, ParameterType.Integer),
        "total_simulations": ParameterSchema(True, ParameterType.Integer),
    },  # Client will perform discovery, reading and response handling at the specified rate for total_simulations
}


def valid_action_names_factory() -> set[str]:
    """Produces the collection of valid action names.

    Just really ensures anyone adding to the above doesn't overwrite those used
    in plugins for example.

    Returns:
        Valid action.type strings

    Raises:
        ValueError: if 'type' name is reserved
    """
    valid_names = set()
    reserved_used = set()
    for name in ACTION_PARAMETER_SCHEMA.keys():
        if name in Action.RESERVED_NAMES:
            reserved_used.add(name)
        else:
            valid_names.add(name)

    if len(reserved_used) > 0:
        raise ValueError(f"Action names {reserved_used} are reserved. All reserved: {Action.RESERVED_NAMES}")

    return valid_names


VALID_ACTION_NAMES: set[str] = valid_action_names_factory()


def validate_action_parameters(procedure_name: str, step_name: str, action: Action) -> None:
    """Validates the action parameters for the parent TestProcedure based on the  ACTION_PARAMETER_SCHEMA

    raises TestProcedureDefinitionError on failure"""
    location = f"{procedure_name}.step[{step_name}]"  # Descriptive location

    parameter_schema = ACTION_PARAMETER_SCHEMA.get(action.type, None)
    if parameter_schema is None:
        raise TestProcedureDefinitionError(
            f"{location} has an invalid action name '{action.type}'. Valid Names: {VALID_ACTION_NAMES}"
        )

    validate_parameters(location, action.parameters, parameter_schema)
