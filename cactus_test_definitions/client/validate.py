from cactus_test_definitions.client.actions import Action, validate_action_parameters
from cactus_test_definitions.client.checks import validate_check_parameters
from cactus_test_definitions.client.events import validate_event_parameters
from cactus_test_definitions.client.test_procedures import (
    TestProcedure,
    TestProcedureId,
)
from cactus_test_definitions.errors import TestProcedureDefinitionError


def validate_action(
    procedure: TestProcedure, test_procedure_id: TestProcedureId, location: str, action: Action
) -> None:
    """Handles the full validation of an action's definition for a parent procedure.

    procedure: The parent TestProcedure for action
    test_procedure_id: The name of procedure (used for labelling errors)
    location: Where in procedure can you find action? (used for labelling errors)
    action: The action to validate

    raises TestProcedureDefinitionError on failure
    """
    validate_action_parameters(test_procedure_id, location, action)

    # Provide additional "action specific" validation
    match action.type:
        case "enable-steps" | "remove-steps":
            for step_name in action.parameters["steps"]:
                if step_name not in procedure.steps.keys():
                    raise TestProcedureDefinitionError(
                        f"{test_procedure_id}.{location}. Refers to unknown step '{step_name}'."
                    )


def validate_test_procedure_actions(test_procedure: TestProcedure, test_procedure_id: TestProcedureId) -> None:
    """Validate actions of test procedure steps / preconditions

    Ensure,
    - action has the correct parameters
    - if parameters refer to steps then those steps are defined for the test procedure
    """

    # Validate actions in the preconditions
    if test_procedure.preconditions:
        if test_procedure.preconditions.actions:
            for action in test_procedure.preconditions.actions:
                validate_action(test_procedure, test_procedure_id, "Precondition", action)

        if test_procedure.preconditions.init_actions:
            for action in test_procedure.preconditions.init_actions:
                validate_action(test_procedure, test_procedure_id, "Precondition", action)

    # Validate actions that exist on steps
    for step_name, step in test_procedure.steps.items():
        for action in step.actions:
            validate_action(test_procedure, test_procedure_id, step_name, action)


def validate_test_procedure_checks(test_procedure: TestProcedure, test_procedure_id: TestProcedureId) -> None:
    """Validate checks of a test procedure

    Ensure,
    - check has the correct parameters
    """

    if test_procedure.criteria and test_procedure.criteria.checks:
        for check in test_procedure.criteria.checks:
            validate_check_parameters(f"{test_procedure_id}: Criteria", check)

    if test_procedure.preconditions and test_procedure.preconditions.checks:
        for check in test_procedure.preconditions.checks:
            validate_check_parameters(f"{test_procedure_id}: Preconditions", check)

    for step_name, step in test_procedure.steps.items():
        if step.event.checks:
            for check in step.event.checks:
                validate_check_parameters(f"{test_procedure_id}: Step {step_name}", check)


def validate_test_procedure_events(test_procedure: TestProcedure, test_procedure_id: TestProcedureId) -> None:
    """Validate events of test procedure steps

    Ensure,
    - event has the correct parameters
    """

    if test_procedure.steps:
        for step_name, step in test_procedure.steps.items():
            validate_event_parameters(test_procedure_id, step_name, step.event)


def validate_test_procedure(test_procedure: TestProcedure, test_procedure_id: TestProcedureId) -> None:
    """Performs additional "high level" validation of a test procedure. (eg: ensuring all action names are valid)

    raises TestProcedureDefinitionError on error"""
    validate_test_procedure_actions(test_procedure, test_procedure_id)
    validate_test_procedure_checks(test_procedure, test_procedure_id)
    validate_test_procedure_events(test_procedure, test_procedure_id)
