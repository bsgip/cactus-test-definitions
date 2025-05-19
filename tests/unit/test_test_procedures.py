from cactus_test_definitions.test_procedures import TestProcedureConfig


def test_available_tests_populated():
    """Force test procedures to load and ensure they all validate (and we at least have a few)"""
    assert len(TestProcedureConfig.available_tests()) > 0
