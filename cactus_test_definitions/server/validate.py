from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.server.actions import validate_action_parameters
from cactus_test_definitions.server.admin_instructions import validate_admin_instruction_parameters
from cactus_test_definitions.server.checks import validate_check_parameters
from cactus_test_definitions.server.test_procedures import (
    TestProcedure,
    TestProcedureId,
)


def validate_test_procedure(test_procedure: TestProcedure, test_procedure_id: TestProcedureId) -> None:
    # Check preconditions
    if not test_procedure.preconditions.required_clients:
        raise TestProcedureDefinitionError(
            f"{test_procedure_id} has no RequiredClients element. At least 1 entry required"
        )
    required_clients_by_id = dict((rc.id, rc) for rc in test_procedure.preconditions.required_clients)

    for step in test_procedure.steps:
        validate_action_parameters(test_procedure_id, step.id, step.action)

        # Validate step checks
        if step.checks:
            for check in step.checks:
                validate_check_parameters(test_procedure_id, check)

        # Validate admin instructions
        if step.admin_instructions:
            for instruction in step.admin_instructions:
                validate_admin_instruction_parameters(test_procedure_id, step.id, instruction)
                if instruction.client is not None and instruction.client not in required_clients_by_id:
                    raise TestProcedureDefinitionError(
                        f"{test_procedure_id}.step[{step.id}].admin_instruction[{instruction.type}] "
                        f"references client '{instruction.client}' that isn't listed in RequiredClients."
                    )

        # Ensure client exists
        if step.client is not None and step.client not in required_clients_by_id:
            raise TestProcedureDefinitionError(
                f"{test_procedure_id} reference client {step.client} that isn't listed in RequiredClients."
            )
