from dataclasses import dataclass
from typing import Any

from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.parameters import (
    ParameterSchema,
    ParameterType,
    validate_parameters,
)
from cactus_test_definitions.variable_expressions import parse_variable_expression_body, try_extract_variable_expression


@dataclass
class AdminInstruction:
    type: str
    client: str | None = None  # The RequiredClient.id this instruction refers to. If None - applies to the 0th client
    parameters: dict[str, Any] = None  # type: ignore # Forced in __post_init__

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

        for k, v in self.parameters.items():
            variable_expr = try_extract_variable_expression(v)
            if variable_expr:
                self.parameters[k] = parse_variable_expression_body(variable_expr, k)


# The parameter schema for each admin instruction type, keyed by type name.
# Admin instructions describe desired server state to be sent to the server's admin API.
ADMIN_INSTRUCTION_PARAMETER_SCHEMA: dict[str, dict[str, ParameterSchema]] = {
    # Ensure an EndDevice registration exists (or does not exist) for the client.
    # has_der_list=True ensures the DER record includes DERCapabilityLink, DERSettingsLink, DERStatusLink.
    "ensure-end-device": {
        "registered": ParameterSchema(True, ParameterType.Boolean),
        "client_type": ParameterSchema(False, ParameterType.String),  # "device" or "aggregator"
        "has_der_list": ParameterSchema(False, ParameterType.Boolean),
        "has_registration_link": ParameterSchema(False, ParameterType.Boolean),
    },
    # Ensure the MirrorUsagePointList is empty (no registered MUPs).
    "ensure-mup-list-empty": {},
    # Ensure a FunctionSetAssignment is attached to the client's EndDevice.
    # annotation is a label used to reference this FSA from later instructions (e.g. in ensure-der-program).
    "ensure-fsa": {
        "annotation": ParameterSchema(False, ParameterType.String),
        "primacy": ParameterSchema(False, ParameterType.Integer),
    },
    # Ensure a DERProgram exists within the FSA identified by fsa_annotation.
    "ensure-der-program": {
        "fsa_annotation": ParameterSchema(False, ParameterType.String),
        "primacy": ParameterSchema(False, ParameterType.Integer),
    },
    # Grant or revoke a client's access to the aggregator tenancy under test.
    # Covers the ENABLE/REMOVE ACCESS pattern from multi-client certificate rotation tests.
    "set-client-access": {
        "granted": ParameterSchema(True, ParameterType.Boolean),
    },
    # Ensure the DERControlList is accessible to the client, optionally requiring it to be subscribable.
    "ensure-der-control-list": {
        "subscribable": ParameterSchema(False, ParameterType.Boolean),
    },
    # Create a DERControl on the server. All control mode parameters are optional;
    # at least one should be provided. Variable expressions (e.g. $(setMaxW * 0.3)) are supported.
    # status: "active" (default) sets startTime in the past; "scheduled" sets startTime in the future.
    # Multiple "scheduled" controls should be stacked sequentially (non-overlapping) by the implementation.
    "create-der-control": {
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
    "create-default-der-control": {
        "opModExpLimW": ParameterSchema(False, ParameterType.Float),
        "opModImpLimW": ParameterSchema(False, ParameterType.Float),
        "opModGenLimW": ParameterSchema(False, ParameterType.Float),
        "opModLoadLimW": ParameterSchema(False, ParameterType.Float),
        "setGradW": ParameterSchema(False, ParameterType.Integer),
        "primacy": ParameterSchema(False, ParameterType.Integer),
    },
    # Cancel active DERControls. If all=True, cancel all active controls; otherwise cancel the most recent.
    "clear-der-controls": {
        "all": ParameterSchema(False, ParameterType.Boolean),
    },
    # Set the poll rate for a given CSIP-Aus resource (e.g. DERProgramList, EndDeviceList).
    "set-poll-rate": {
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
        "rate_seconds": ParameterSchema(True, ParameterType.Integer),
    },
    # Set the post rate for a MirrorUsagePoint resource.
    "set-post-rate": {
        "resource": ParameterSchema(True, ParameterType.CSIPAusResource),
        "rate_seconds": ParameterSchema(True, ParameterType.Integer),
    },
}
VALID_ADMIN_INSTRUCTION_NAMES: set[str] = set(ADMIN_INSTRUCTION_PARAMETER_SCHEMA.keys())


def validate_admin_instruction_parameters(procedure_name: str, step_name: str, instruction: AdminInstruction) -> None:
    """Validates the parameters of an AdminInstruction against ADMIN_INSTRUCTION_PARAMETER_SCHEMA.

    raises TestProcedureDefinitionError on failure"""
    location = f"{procedure_name}.step[{step_name}].admin_instruction[{instruction.type}]"

    parameter_schema = ADMIN_INSTRUCTION_PARAMETER_SCHEMA.get(instruction.type, None)
    if parameter_schema is None:
        raise TestProcedureDefinitionError(
            f"{location} has an invalid admin instruction type '{instruction.type}'. "
            f"Valid types: {VALID_ADMIN_INSTRUCTION_NAMES}"
        )

    validate_parameters(location, instruction.parameters, parameter_schema)
