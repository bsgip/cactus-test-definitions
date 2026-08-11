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


def validate_der_program_exists_before_default_control(
    test_procedure: TestProcedure, test_procedure_id: TestProcedureId
) -> None:
    """set-default-der-control (without an explicit derp_id) requires a DERProgram to already exist - the runner
    will not create one implicitly (unlike create-der-control). Ensure create-der-program/create-der-control always
    precedes such a call, in actual execution order: init_actions, then preconditions actions, then step actions.

    raises TestProcedureDefinitionError on failure
    """
    ordered_action_lists: list[tuple[list[Action] | None, str]] = []
    if test_procedure.preconditions:
        ordered_action_lists.append((test_procedure.preconditions.init_actions, "Precondition init_actions"))
        ordered_action_lists.append((test_procedure.preconditions.actions, "Precondition actions"))
    ordered_action_lists.extend((step.actions, step_name) for step_name, step in test_procedure.steps.items())

    has_der_program = False
    for actions, location in ordered_action_lists:
        for action in actions or []:
            if action.type in ("create-der-program", "create-der-control"):
                has_der_program = True
            elif (
                action.type == "set-default-der-control"
                and action.parameters.get("derp_id") is None
                and not has_der_program
            ):
                raise TestProcedureDefinitionError(
                    f"{test_procedure_id}.{location}. set-default-der-control has no derp_id and no "
                    "create-der-program/create-der-control has executed yet - the runner has no DERProgram "
                    "to attach the DefaultDERControl to."
                )


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
    validate_der_program_exists_before_default_control(test_procedure, test_procedure_id)
