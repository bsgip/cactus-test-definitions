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
class AdminInstruction:
    type: str
    description: str
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
