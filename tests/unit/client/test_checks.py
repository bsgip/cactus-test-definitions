import pytest
from cactus_test_definitions import variable_expressions as varexps
from cactus_test_definitions.client.checks import Check, validate_check_parameters
from cactus_test_definitions.errors import TestProcedureDefinitionError


@pytest.mark.parametrize(
    "check, is_valid",
    [
        (Check("foo", {}), False),  # Unknown check
        (Check("readings-site-active-power", {}), True),
        (Check("readings-site-active-power", {"minimum_count": "3"}), False),
        (Check("readings-site-active-power", {"minimum_count": 3}), True),
        (Check("readings-site-active-power", {"minimum_count": 3, "minimum_level": 12.3}), True),
        (Check("readings-site-active-power", {"minimum_count": 3, "maximum_level": 12.3}), True),
        (Check("readings-site-active-power", {"minimum_count": 3, "minimum_level": 12.3, "maximum_level": 12.3}), True),
        (
            Check(
                "readings-site-active-power",
                {"minimum_count": 3, "minimum_level": 12.3, "maximum_level": 12.3, "window_seconds": 12.3},
            ),
            False,
        ),
        (
            Check(
                "readings-site-active-power",
                {"minimum_count": 3, "minimum_level": 12.3, "maximum_level": 12.3, "window_seconds": 180},
            ),
            True,
        ),
        (
            Check(
                "readings-site-active-power",
                {"minimum_count": 3, "minimum_level": 12.3, "maximum_level": 12.3, "window_seconds": -180},
            ),
            False,
        ),
        (Check("der-settings-contents", {"setGradW": 27}), True),
        (Check("der-settings-contents", {"doeModesEnabled_set": "0f"}), True),
        (Check("der-settings-contents", {"doeModesEnabled_unset": "0f"}), True),
        (Check("der-settings-contents", {"modesEnabled_set": "E"}), True),
        (Check("der-settings-contents", {"modesEnabled_unset": "E"}), True),
        (Check("der-settings-contents", {"doeModesEnabled_set": 12}), False),
        (Check("der-settings-contents", {"doeModesEnabled_unset": 12}), False),
        # Storage extension
        (Check("der-settings-contents", {"vppModesEnabled_set": "1"}), True),
        (Check("der-settings-contents", {"vppModesEnabled_unset": "1"}), True),
        (Check("der-capability-contents", {"vppModesSupported_set": "1"}), True),
        (Check("der-capability-contents", {"vppModesSupported_unset": "1"}), True),
        (Check("readings-der-stored-energy", {"minimum_count": 3}), True),
    ],
)
def test_validate_check_parameters(check: Check, is_valid: bool):
    if is_valid:
        validate_check_parameters("foo", check)
    else:
        with pytest.raises(TestProcedureDefinitionError):
            validate_check_parameters("foo", check)


def test_check_expression() -> None:
    """Tests the creation of a Check that has an expression as one of its parameters"""
    type_str = "some_check"
    params = {"setMaxW": "$(this < rtgMaxW)"}
    check = Check(type_str, params)

    check_set_max_w = check.parameters["setMaxW"]
    assert isinstance(check_set_max_w, varexps.Expression)
    assert check_set_max_w.operation == varexps.OperationType.LT
    assert check_set_max_w.lhs_operand == varexps.NamedVariable(varexps.NamedVariableType.DERSETTING_SET_MAX_W)
    assert check_set_max_w.rhs_operand == varexps.NamedVariable(varexps.NamedVariableType.DERCAPABILITY_RTG_MAX_W)
