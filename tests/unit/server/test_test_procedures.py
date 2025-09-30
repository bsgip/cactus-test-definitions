import pytest
from cactus_test_definitions.server.actions import ACTION_PARAMETER_SCHEMA
from cactus_test_definitions.server.test_procedures import (
    TestProcedure,
    TestProcedureConfig,
    TestProcedureId,
)

# Failures here will raise an issue in the test_from_yamlfile test
ALL_TEST_PROCEDURES: list[tuple[str, TestProcedure]] = []
try:
    ALL_TEST_PROCEDURES = [(k, tp) for k, tp in TestProcedureConfig.from_resource().test_procedures.items()]
except Exception:
    pass


def test_ALL_TEST_PROCEDURES_parsed():
    assert len(ALL_TEST_PROCEDURES) > 0


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
def test_each_step_id_unique(tp_id: str, tp: TestProcedure):
    all_ids = [s.id for s in tp.steps]
    assert list(sorted(all_ids)) == list(sorted(set(all_ids)))
    assert len(set((s.id for s in tp.steps))) == len(tp.steps), "All steps must have a unique id property"


@pytest.mark.parametrize("tp_id, tp", ALL_TEST_PROCEDURES)
def test_each_alias_defined(tp_id: str, tp: TestProcedure):
    """Ensures that each test procedure's steps that have actions using an alias... define those aliases in advance"""

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
            assert mup_id and (mup_id not in mup_aliases_found), "mup_id is already defined in this test."
            mup_aliases_found.add(mup_id)
        elif step.action.type == INSERT_MUP_ACTION:
            assert mup_id and (mup_id in mup_aliases_found), "mup_id hasn't been defined yet."
        elif step.action.type == CREATE_SUB_ACTION:
            assert sub_id and (sub_id not in sub_aliases_found), "sub_id is already defined in this test."
            sub_aliases_found.add(sub_id)
        elif step.action.type == DELETE_SUB_ACTION:
            assert sub_id and (sub_id in sub_aliases_found), "sub_id hasn't been defined yet."
