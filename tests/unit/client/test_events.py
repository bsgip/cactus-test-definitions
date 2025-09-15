import pytest
from cactus_test_definitions import variable_expressions as varexps
from cactus_test_definitions.client.events import Event, validate_event_parameters
from cactus_test_definitions.errors import TestProcedureDefinitionError


@pytest.mark.parametrize(
    "event, is_valid",
    [
        (Event("foo", {}), False),  # Unknown check
        (Event("wait", {}), False),
        (Event("wait", {"duration_seconds": "3"}), False),
        (Event("wait", {"duration_seconds": 3}), True),
        (Event("wait", {"duration_seconds": 3, "other": 4}), False),
        (Event("GET-request-received", {"endpoint": "/dcap"}), True),
    ],
)
def test_validate_event_parameters(event: Event, is_valid: bool):
    if is_valid:
        validate_event_parameters("foo", "bar", event)
    else:
        with pytest.raises(TestProcedureDefinitionError):
            validate_event_parameters("foo", "bar", event)


def test_event_expression() -> None:
    """Tests the creation of an Event that has an expression as one of its parameters"""
    type_str = "some_event"
    params = {"setMaxW": "$(this < rtgMaxW)"}
    event = Event(type_str, params)

    check_set_max_w = event.parameters["setMaxW"]
    assert isinstance(check_set_max_w, varexps.Expression)
    assert check_set_max_w.operation == varexps.OperationType.LT
    assert check_set_max_w.lhs_operand == varexps.NamedVariable(varexps.NamedVariableType.DERSETTING_SET_MAX_W)
    assert check_set_max_w.rhs_operand == varexps.NamedVariable(varexps.NamedVariableType.DERCAPABILITY_RTG_MAX_W)
