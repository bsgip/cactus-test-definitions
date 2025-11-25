import pytest
from cactus_test_definitions.server.actions import ACTION_PARAMETER_SCHEMA
from cactus_test_definitions.server.test_procedures import (
    TestProcedureId,
    get_test_procedure,
)
from cactus_test_definitions.server.validate import validate_test_procedure


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_TestProcedure_individually_valid(tp_id: TestProcedureId):
    """Tests that each TestProcedureId can be loaded via get_test_procedure without issue AND that it
    passes validate_test_procedure."""
    tp = get_test_procedure(tp_id)
    assert tp.steps, "There should be steps configured"
    validate_test_procedure(tp, tp_id)


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_each_step_id_unique(tp_id: TestProcedureId):
    tp = get_test_procedure(tp_id)
    all_ids = [s.id for s in tp.steps]
    assert list(sorted(all_ids)) == list(sorted(set(all_ids)))
    assert len(set((s.id for s in tp.steps))) == len(tp.steps), "All steps must have a unique id property"


@pytest.mark.parametrize("tp_id", TestProcedureId)
def test_each_alias_defined(tp_id: str):
    """Ensures that each test procedure's steps that have actions using an alias... define those aliases in advance"""

    tp = get_test_procedure(tp_id)

    # sanity check - make sure we are looking for the action names that are valid
    UPSERT_MUP_ACTION = "upsert-mup"
    INSERT_MUP_ACTION = "insert-readings"
    CREATE_SUB_ACTION = "create-subscription"
    DELETE_SUB_ACTION = "delete-subscription"
    assert UPSERT_MUP_ACTION in ACTION_PARAMETER_SCHEMA, "If this fails - the action name has changed. Update this test"
    assert INSERT_MUP_ACTION in ACTION_PARAMETER_SCHEMA, "If this fails - the action name has changed. Update this test"
    assert CREATE_SUB_ACTION in ACTION_PARAMETER_SCHEMA, "If this fails - the action name has changed. Update this test"
    assert DELETE_SUB_ACTION in ACTION_PARAMETER_SCHEMA, "If this fails - the action name has changed. Update this test"

    mup_aliases_found: set[str] = set()
    sub_aliases_found: set[str] = set()
    for step in tp.steps:
        if step.action.parameters:
            mup_id = step.action.parameters.get("mup_id", None)
            sub_id = step.action.parameters.get("sub_id", None)
        else:
            mup_id = None
            sub_id = None

        if step.action.type == UPSERT_MUP_ACTION:
            mup_aliases_found.add(mup_id)
        elif step.action.type == INSERT_MUP_ACTION:
            assert mup_id and (mup_id in mup_aliases_found), "mup_id hasn't been defined yet."
        elif step.action.type == CREATE_SUB_ACTION:
            assert sub_id and (sub_id not in sub_aliases_found), "sub_id is already defined in this test."
            sub_aliases_found.add(sub_id)
        elif step.action.type == DELETE_SUB_ACTION:
            assert sub_id and (sub_id in sub_aliases_found), "sub_id hasn't been defined yet."
