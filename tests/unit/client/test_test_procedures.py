import pytest
from cactus_test_definitions.client.test_procedures import (
    TestProcedure,
    TestProcedureConfig,
    TestProcedureId,
)
from cactus_test_definitions.variable_expressions import (
    NamedVariableType,
    has_named_variable,
)

# Failures here will raise an issue in the test_from_yamlfile test
ALL_TEST_PROCEDURES: list[tuple[str, TestProcedure]] = []
try:
    ALL_TEST_PROCEDURES = [(k, tp) for k, tp in TestProcedureConfig.from_resource().test_procedures.items()]
except Exception:
    pass


def test_from_yamlfile():
    """This test confirms the standard test procedure yaml file (intended for production use)
    can be read and converted to the appropriate dataclasses.
    """
    test_procedures = TestProcedureConfig.from_resource()
    test_procedures.validate()


def test_TestProcedureId_synchronised():
    """Ensures that TestProcedureId is in sync with all available TestProcedures"""
    available_tests = set(TestProcedureConfig.available_tests())
    for t in available_tests:
        assert t in TestProcedureId, "TestProcedureConfig has a procedure not encoded in TestProcedureId"

    # By convention - test ALL-01 will be an enum ALL_01
    # for t in (t.replace("_", "-") for t in TestProcedureId):
    for t in TestProcedureId:
        assert t.value in available_tests, "TestProcedureId has extra procedures not found in TestProcedureConfig"


def test_available_tests_populated():
    """Force test procedures to load and ensure they all validate (and we at least have a few)"""
    assert len(TestProcedureConfig.available_tests()) > 0


@pytest.mark.parametrize("tp_id, tp", ALL_TEST_PROCEDURES)
def test_each_step_accessible(tp_id: str, tp: TestProcedure):
    """Ensures that each test procedure's steps are enabled/removed once. Failures here indicate a bad reference to
    enable/remove steps"""

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
        assert (
            removal_count[step_name] == 1
        ), f"{step_name}: Each test should be removed once otherwise the test cannot complete"

        if step_name == first_step:
            assert enabled_count[step_name] == 0, f"{step_name}: The first test step is already enabled"
        else:
            assert (
                enabled_count[step_name] == 1
            ), f"{step_name}: Each test should be added once - not expecting loops of steps"


@pytest.mark.parametrize("tp_id, tp", ALL_TEST_PROCEDURES)
def test_each_step_connected(tp_id: str, tp: TestProcedure):
    """Interprets each test a graph of steps linking to other steps (via enable-steps). Passes if the test procedure
    is fully connected from the first step (i.e. there are no isolated islands of steps that can't be reached from
    the first step)"""

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


@pytest.mark.parametrize("_, tp", ALL_TEST_PROCEDURES)
def test_procedures_have_required_preconditions(_: str, tp: TestProcedure):

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
