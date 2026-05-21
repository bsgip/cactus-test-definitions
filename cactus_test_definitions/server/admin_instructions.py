from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cactus_test_definitions.parameters import (
    ParameterSchema,
    ParameterType,
    validate_parameters,
)
from cactus_test_definitions.variable_expressions import parse_variable_expression_body, try_extract_variable_expression


class AdminInstructionType(StrEnum):
    ENSURE_END_DEVICE = "ensure-end-device"
    ENSURE_FSA = "ensure-fsa"
    ENSURE_DER_PROGRAM = "ensure-der-program"
    ENSURE_DER_CONTROL_LIST = "ensure-der-control-list"
    ENSURE_MUP_LIST_EMPTY = "ensure-mup-list-empty"
    CREATE_DER_CONTROL = "create-der-control"
    CREATE_DEFAULT_DER_CONTROL = "create-default-der-control"
    CLEAR_DER_CONTROLS = "clear-der-controls"
    SET_POLL_RATE = "set-poll-rate"
    SET_POST_RATE = "set-post-rate"
    SET_CLIENT_ACCESS = "set-client-access"


@dataclass
class AdminInstruction:
    type: AdminInstructionType
    client: str | None = None  # The RequiredClient.id this instruction refers to. If None - applies to the 0th client
    parameters: dict[str, Any] = None  # type: ignore # Forced in __post_init__

    def __post_init__(self) -> None:
        if not isinstance(self.type, AdminInstructionType):
            self.type = AdminInstructionType(self.type)

        if self.parameters is None:
            self.parameters = {}

        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)


# The parameter schema for each admin instruction type, keyed by type name.
# Admin instructions describe desired server state to be sent to the server's admin API.
ADMIN_INSTRUCTION_PARAMETER_SCHEMA: dict[AdminInstructionType, dict[str, ParameterSchema]] = {
    # Ensure an EndDevice registration exists (or does not exist) for the client.
    # has_der_list=True ensures the DER record includes DERCapabilityLink, DERSettingsLink, DERStatusLink.
    AdminInstructionType.ENSURE_END_DEVICE: {
        "registered": ParameterSchema(True, ParameterType.Boolean),
        "client_type": ParameterSchema(False, ParameterType.String),  # "device" or "aggregator"
        "has_der_list": ParameterSchema(False, ParameterType.Boolean),
        "has_registration_link": ParameterSchema(False, ParameterType.Boolean),
    },
    # Ensure the MirrorUsagePointList is empty (no registered MUPs).
    AdminInstructionType.ENSURE_MUP_LIST_EMPTY: {},
    # Ensure a FunctionSetAssignment is attached to the client's EndDevice.
    # annotation is a label used to reference this FSA from later instructions (e.g. in ensure-der-program).
    AdminInstructionType.ENSURE_FSA: {
        "annotation": ParameterSchema(False, ParameterType.String),
        "primacy": ParameterSchema(False, ParameterType.Integer),
    },
    # Ensure a DERProgram exists within the FSA identified by fsa_annotation.
    AdminInstructionType.ENSURE_DER_PROGRAM: {
        "fsa_annotation": ParameterSchema(False, ParameterType.String),
        "primacy": ParameterSchema(False, ParameterType.Integer),
    },
    # Grant or revoke a client's access to the aggregator tenancy under test.
    # Covers the ENABLE/REMOVE ACCESS pattern from multi-client certificate rotation tests.
    AdminInstructionType.SET_CLIENT_ACCESS: {
        "granted": ParameterSchema(True, ParameterType.Boolean),
    },
    # Ensure the DERControlList is accessible to the client, optionally requiring it to be subscribable.
    AdminInstructionType.ENSURE_DER_CONTROL_LIST: {
        "subscribable": ParameterSchema(False, ParameterType.Boolean),
    },
    # Create a DERControl on the server. All control mode parameters are optional;
    # at least one should be provided. Variable expressions (e.g. $(setMaxW * 0.3)) are supported.
    # status: "active" (default) sets startTime in the past; "scheduled" sets startTime in the future.
    # Multiple "scheduled" controls should be stacked sequentially (non-overlapping) by the implementation.
    AdminInstructionType.CREATE_DER_CONTROL: {
        "status": ParameterSchema(True, ParameterType.String),  # "active" or "scheduled"
        "opModExpLimW": ParameterSchema(False, ParameterType.Float),
        "opModImpLimW": ParameterSchema(False, ParameterType.Float),
        "opModGenLimW": ParameterSchema(False, ParameterType.Float),
        "opModLoadLimW": ParameterSchema(False, ParameterType.Float),
        "opModConnect": ParameterSchema(False, ParameterType.Boolean),
        "opModEnergize": ParameterSchema(False, ParameterType.Boolean),
        "opModFixedW": ParameterSchema(False, ParameterType.Float),
        "rampTms": ParameterSchema(False, ParameterType.Integer),
        "randomizeStart_seconds": ParameterSchema(False, ParameterType.Integer),
        "duration_seconds": ParameterSchema(False, ParameterType.Integer),
        "primacy": ParameterSchema(False, ParameterType.Integer),
        "start_offset_seconds": ParameterSchema(False, ParameterType.Integer),
    },
    # Create or replace the DefaultDERControl on the server. Variable expressions are supported.
    AdminInstructionType.CREATE_DEFAULT_DER_CONTROL: {
        "opModExpLimW": ParameterSchema(False, ParameterType.Float),
        "opModImpLimW": ParameterSchema(False, ParameterType.Float),
        "opModGenLimW": ParameterSchema(False, ParameterType.Float),
        "opModLoadLimW": ParameterSchema(False, ParameterType.Float),
        "setGradW": ParameterSchema(False, ParameterType.Integer),
        "primacy": ParameterSchema(False, ParameterType.Integer),
    },
    # Cancel active DERControls. If all=True, cancel all active controls; otherwise cancel the most recent.
    AdminInstructionType.CLEAR_DER_CONTROLS: {
        "all": ParameterSchema(False, ParameterType.Boolean),
    },
    # Set the poll rate for a given CSIP-Aus resource (e.g. DERProgramList, EndDeviceList).
    AdminInstructionType.SET_POLL_RATE: {
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
        "rate_seconds": ParameterSchema(True, ParameterType.Integer),
    },
    # Set the post rate for a MirrorUsagePoint resource.
    AdminInstructionType.SET_POST_RATE: {
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
        "rate_seconds": ParameterSchema(True, ParameterType.Integer),
    },
}


def validate_admin_instruction_parameters(procedure_name: str, step_name: str, instruction: AdminInstruction) -> None:
    """Validates the parameters of an AdminInstruction against ADMIN_INSTRUCTION_PARAMETER_SCHEMA.

    raises TestProcedureDefinitionError on failure"""
    location = f"{procedure_name}.step[{step_name}].admin_instruction[{instruction.type}]"
    parameter_schema = ADMIN_INSTRUCTION_PARAMETER_SCHEMA[instruction.type]
    validate_parameters(location, instruction.parameters, parameter_schema)
