from pathlib import Path
from typing import Any

import pytest
from cactus_test_definitions.client.actions import ACTION_PARAMETER_SCHEMA, Action
from cactus_test_definitions.client.checks import CHECK_PARAMETER_SCHEMA, Check
from cactus_test_definitions.client.test_procedures import (
    TestProcedure,
    TestProcedureId,
    get_test_procedure,
    parse_test_procedure,
)
from cactus_test_definitions.client.validate import validate_test_procedure
from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.variable_expressions import (
    NamedVariableType,
    has_named_variable,
)


def collect_action_param_values(tp: TestProcedure, action_type: str, param_name: str) -> list[Any | None]:
    """Collects all values of an action's parameter across all steps and preconditions."""

    assert action_type in ACTION_PARAMETER_SCHEMA, "Sanity check to catch typos / changes in definitions"
    assert param_name in ACTION_PARAMETER_SCHEMA[action_type], "Sanity check to catch typos / changes in definitions"

    all_actions: list[Action] = []
    if tp.preconditions:
        if tp.preconditions.init_actions:
            all_actions.extend(tp.preconditions.init_actions)
        if tp.preconditions.actions:
            all_actions.extend(tp.preconditions.actions)
    for step in tp.steps.values():
        all_actions.extend(step.actions)

    # Extract
    extracted_values: list[Any] = []
    for action in all_actions:
        if action.type == action_type and param_name in action.parameters:
            extracted_values.append(action.parameters.get(param_name, None))
    return extracted_values


def collect_check_param_values(tp: TestProcedure, check_type: str, param_name: str) -> list[Any | None]:
    """Collects all values of a check's parameter across all steps and preconditions."""

    assert check_type in CHECK_PARAMETER_SCHEMA, "Sanity check to catch typos / changes in definitions"
    assert param_name in CHECK_PARAMETER_SCHEMA[check_type], "Sanity check to catch typos / changes in definitions"

    all_checks: list[Check] = []
    if tp.preconditions:
        if tp.preconditions.checks:
            all_checks.extend(tp.preconditions.checks)

    if tp.criteria:
        if tp.criteria.checks:
            all_checks.extend(tp.criteria.checks)

    for step in tp.steps.values():
        if step.event.checks:
            all_checks.extend(step.event.checks)

    # Extract
    extracted_values: list[Any] = []
    for check in all_checks:
        if check.type == check_type and param_name in check.parameters:
            extracted_values.append(check.parameters.get(param_name, None))
    return extracted_values


@pytest.mark.parametrize(
    "tp_file",
    [
        Path("tests/data/client/tp_invalid_bad_param.yaml"),
        Path("tests/data/client/tp_invalid_bad_step_enable.yaml"),
        Path("tests/data/client/tp_invalid_bad_step_remove.yaml"),
    ],
)
def test_TestProcedure_invalid_examples(tp_file: Path):
    with open(tp_file, "r") as fp:
        tp = parse_test_procedure(fp.read())

    with pytest.raises(TestProcedureDefinitionError):
        validate_test_procedure(tp, TestProcedureId.ALL_01)


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_TestProcedure_individually_valid(tp_id: TestProcedureId):
    """Tests that each TestProcedureId can be loaded via get_test_procedure without issue AND that it
    passes validate_test_procedure."""
    tp = get_test_procedure(tp_id)
    assert tp.steps, "There should be steps configured"
    validate_test_procedure(tp, tp_id)


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_each_step_accessible(tp_id: TestProcedureId):  # noqa: C901
    """Ensures that each test procedure's steps are enabled/removed once. Failures here indicate a bad reference to
    enable/remove steps"""

    tp = get_test_procedure(tp_id)

    # We need to identify any steps as "ignored"
    ALL_STEPS_COMPLETE = "all-steps-complete"
    IGNORED_STEPS = "ignored_steps"
    assert ALL_STEPS_COMPLETE in CHECK_PARAMETER_SCHEMA, "Sanity check to catch changing names"
    assert IGNORED_STEPS in CHECK_PARAMETER_SCHEMA[ALL_STEPS_COMPLETE], "Sanity check to catch changing names"
    ignored_steps: set[str] = set()
    if tp.criteria and tp.criteria.checks:
        for check in tp.criteria.checks:
            if check.type == ALL_STEPS_COMPLETE:
                ignored_steps.update(check.parameters.get(IGNORED_STEPS, []))

    first_step = [k for k in tp.steps.keys()][0]
    step_names = set(tp.steps.keys())

    removal_count = dict([(s, 0) for s in step_names])
    enabled_count = dict([(s, 0) for s in step_names])

    # Tally up the number of times each step is added/removed via actions
    for s in tp.steps.values():
        for enabled_name in [name for a in s.actions if a.type == "enable-steps" for name in a.parameters["steps"]]:
            enabled_count[enabled_name] = enabled_count[enabled_name] + 1
        for removed_name in [name for a in s.actions if a.type == "remove-steps" for name in a.parameters["steps"]]:
            removal_count[removed_name] = removal_count[removed_name] + 1

    # Also check the preconditions for actions
    if tp.preconditions and tp.preconditions.actions:
        for enabled_name in [
            name for a in tp.preconditions.actions if a.type == "enable-steps" for name in a.parameters["steps"]
        ]:
            enabled_count[enabled_name] = enabled_count[enabled_name] + 1
        for removed_name in [
            name for a in tp.preconditions.actions if a.type == "remove-steps" for name in a.parameters["steps"]
        ]:
            removal_count[removed_name] = removal_count[removed_name] + 1

    # Each test should be added once and removed once
    for step_name in step_names:
        if step_name not in ignored_steps:
            assert (
                removal_count[step_name] == 1
            ), f"{step_name}: Each test should be removed once otherwise the test cannot complete"

        if step_name == first_step:
            assert enabled_count[step_name] == 0, f"{step_name}: The first test step is already enabled"
        else:
            assert (
                enabled_count[step_name] == 1
            ), f"{step_name}: Each test should be added once - not expecting loops of steps"


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_each_step_connected(tp_id: TestProcedureId):
    """Interprets each test a graph of steps linking to other steps (via enable-steps). Passes if the test procedure
    is fully connected from the first step (i.e. there are no isolated islands of steps that can't be reached from
    the first step)"""

    tp = get_test_procedure(tp_id)

    first_step = [k for k in tp.steps.keys()][0]
    step_names = set(tp.steps.keys())

    step_links_by_name: dict[str, list[str]] = {}
    for step_name in step_names:
        step = tp.steps[step_name]
        child_step_names = [name for a in step.actions if a.type == "enable-steps" for name in a.parameters["steps"]]
        step_links_by_name[step_name] = child_step_names

    # Walk through our simple graph/tree - make sure we visit every node in that tree
    def gather_connected_steps(links: dict[str, list[str]], node: str, visited_nodes: set[str]) -> None:
        if node in visited_nodes:
            return
        visited_nodes.add(node)
        for child in links[node]:
            gather_connected_steps(links, child, visited_nodes)

    visited_nodes: set[str] = set()
    gather_connected_steps(step_links_by_name, first_step, visited_nodes)

    # Also note that steps might be started as a precondition - so include those as visited too
    if tp.preconditions and tp.preconditions.actions:
        for n in [name for a in tp.preconditions.actions if a.type == "enable-steps" for name in a.parameters["steps"]]:
            visited_nodes.add(n)

    assert (
        step_names == visited_nodes
    ), "Missing entries here indicate a step (or steps) that can't be reached from the root node"


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_procedures_have_required_preconditions(tp_id: TestProcedureId):

    tp = get_test_procedure(tp_id)

    # Immediate start implies that EndDevice registration will happen during the test body - these tests
    # don't require end-device-contents (as it will cause the test to fail anyway)
    is_immediate_start = tp.preconditions is not None and tp.preconditions.immediate_start
    if not is_immediate_start:
        assert tp.preconditions is not None, "Expected precondition check 'end-device-contents'"
        assert tp.preconditions.checks is not None, "Expected precondition check 'end-device-contents'"
        assert any(
            [check.type == "end-device-contents" for check in tp.preconditions.checks]
        ), "Expected precondition check 'end-device-contents'"

    # Check 'der-settings-contents' present if any precondition action parameter references setMaxW
    if tp.preconditions is not None and tp.preconditions.actions is not None:
        for action in tp.preconditions.actions:
            if action.parameters is not None:
                if any(
                    [
                        has_named_variable(
                            parameter_value=parameter, named_variable=NamedVariableType.DERSETTING_SET_MAX_W
                        )
                        for parameter in action.parameters.values()
                    ]
                ):
                    assert tp.preconditions.checks is not None
                    assert any([check.type == "der-settings-contents" for check in tp.preconditions.checks])


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_tag_references_exist(tp_id: TestProcedureId):
    """Ensures that action/check that relies on a "reference" tag (eg create-rate-component and tariff_profile_tag)
    has been created. We can't guarantee that the reference happens AFTER creation but we can catch referencing tags
    that do NOT exist."""

    tp = get_test_procedure(tp_id)

    # tuple of [action_name, action_param, parent_action_name, parent_action_tag_param]
    ACTION_REFS_TO_CHECK = [
        ("create-rate-component", "tariff_profile_tag", "create-tariff-profile", "tag"),
        ("create-time-tariff-interval", "rate_component_tag", "create-rate-component", "tag"),
        ("cancel-time-tariff-intervals", "tag", "create-time-tariff-interval", "tag"),
        ("delete-rate-component", "tag", "create-rate-component", "tag"),
    ]

    # tuple of [check_name, check_param, parent_action_name, parent_action_tag_param]
    CHECK_REFS_TO_CHECK = [
        ("response-contents", "subject_tag", "create-der-control", "tag"),
        ("price-response-contents", "subject_tag", "create-time-tariff-interval", "tag"),
    ]

    for action_type, action_ref, parent_action, parent_tag in ACTION_REFS_TO_CHECK:
        all_parent_values = collect_action_param_values(tp, parent_action, parent_tag)
        for ref_value in collect_action_param_values(tp, action_type, action_ref):
            if ref_value is not None:
                assert ref_value in all_parent_values, (
                    f"{action_type} {action_ref} is '{ref_value}' but a corresponding {parent_action} {parent_tag}"
                    + f" couldn't be found in {all_parent_values}"
                )

    for check_type, check_ref, parent_action, parent_tag in CHECK_REFS_TO_CHECK:
        all_parent_values = collect_action_param_values(tp, parent_action, parent_tag)
        for ref_value in collect_check_param_values(tp, check_type, check_ref):
            if ref_value is not None:
                assert ref_value in all_parent_values, (
                    f"{check_type} {check_ref} is '{ref_value}' but a corresponding {parent_action} {parent_tag}"
                    + f" couldn't be found in {all_parent_values}"
                )


@pytest.mark.parametrize("tp_id", list(TestProcedureId))
def test_resource_tags_unique(tp_id: TestProcedureId):
    """Ensures that all "create-X" tags within a single test procedure are distinct."""

    # These are the create-X actions/tag that we want to enforce uniqueness for
    ACTIONS_WITH_PARAM = [
        ("create-der-control", "tag"),
        ("create-tariff-profile", "tag"),
        ("create-rate-component", "tag"),
        ("create-time-tariff-interval", "tag"),
    ]

    tp = get_test_procedure(tp_id)
    for action_name, param_name in ACTIONS_WITH_PARAM:
        tags = collect_action_param_values(tp, action_name, param_name)
        seen: set[str] = set()
        for tag in tags:
            assert tag not in seen, f"{tp_id}: duplicate {action_name} {param_name} {tag!r}"
            seen.add(tag)
