from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from cactus_test_definitions.client.test_procedures import Action
from cactus_test_definitions.variable_expressions import (
    Constant,
    Expression,
    NamedVariable,
    NamedVariableType,
    OperationType,
    UnparseableVariableExpressionError,
    has_named_variable,
    is_resolvable_variable,
    parse_time_delta,
    parse_variable_expression_body,
    try_extract_variable_expression,
    snake_to_camel,
    named_variable_repr,
    operation_repr,
    BaseExpression,
)


@pytest.mark.parametrize(
    "body, expected",
    [
        (None, None),
        (123, None),
        (12.3, None),
        (["$no_list_inspection"], None),
        ({"$no_dict_inspection": "$no_dict_inspection"}, None),
        (datetime(2001, 2, 3), None),
        ("", None),
        ("  ", None),
        ("$now", "now"),
        ("  $now\n  ", "now"),
        ("$(now)", "now"),
        ("$(now - '5 minutes')", "now - '5 minutes'"),
        ("$(  now - '5 minutes'  )", "  now - '5 minutes'  "),
        ("\\$(now)", None),  # escaped
        ("  \\$(now) ", None),  # escaped
        ("  \\$now ", None),  # escaped
        ("\\$now", None),  # escaped
        ("$variable_with_556", "variable_with_556"),
        ("$(variable_with_556)", "variable_with_556"),
        ("$variable-556", ValueError),  # Don't allow "non variable" data to get omitted
        ("$(variable-556)", "variable-556"),
        ("$longer_variable no spaces", ValueError),
        ("$(longer_variable but include everything)", "longer_variable but include everything"),
        ("$(now", ValueError),  # Unclosed bracket
        (" $(now  ", ValueError),  # Unclosed bracket
        (" $(now foo", ValueError),  # Unclosed bracket
        ("$ invalid_space", ValueError),
        ("$-invalid_char", ValueError),
        ("$", ValueError),  # No variable body included
        ("$ ", ValueError),  # No variable body included
        ("\\$", None),
        ("$()", ValueError),  # No variable body included
        ("\\$()", None),
        (" \\$() ", None),
        ("$(valid) no trailing data", ValueError),  # A string is either a variable or not. Can't substring variables
        ("no leading data $(valid)", ValueError),  # A string is either a variable or not. Can't substring variables
    ],
)
def test_try_extract_variable_expression(body: Any, expected: str | None | type[Exception]):
    """Various test cases that try expose edge cases in try_extract_variable_expression"""
    if isinstance(expected, type):
        with pytest.raises(expected):
            try_extract_variable_expression(body)
    else:
        actual = try_extract_variable_expression(body)
        assert actual is None or isinstance(actual, str)
        assert actual == expected, f"Input string: '{body}'"


@pytest.mark.parametrize(
    "unquoted_raw, expected",
    [
        ("", UnparseableVariableExpressionError),
        ("5 mins", timedelta(minutes=5)),
        ("-5 mins", timedelta(minutes=-5)),
        ("5.23 mins", timedelta(minutes=5.23)),
        ("-5.23 mins", timedelta(minutes=-5.23)),
        ("-0.03 days", timedelta(days=-0.03)),
        ("-0.03   days", timedelta(days=-0.03)),
        ("-0.03days", timedelta(days=-0.03)),
        ("4 minutes", timedelta(minutes=4)),
        ("4 minute", timedelta(minutes=4)),
        ("0 minute", timedelta(minutes=0)),
        ("4 hours", timedelta(hours=4)),
        ("4 hour", timedelta(hours=4)),
        ("4 hrs", timedelta(hours=4)),
        ("4 hr", timedelta(hours=4)),
        ("4 days", timedelta(days=4)),
        ("4 day", timedelta(days=4)),
        ("4 seconds", timedelta(seconds=4)),
        ("4 second", timedelta(seconds=4)),
        ("4 secs", timedelta(seconds=4)),
        ("4 sec", timedelta(seconds=4)),
        ("4 foo", UnparseableVariableExpressionError),  # Unknown unit
        ("4-.2 foo", UnparseableVariableExpressionError),  # Not a number
        ("4.2.3 foo", UnparseableVariableExpressionError),  # Not a number
    ],
)
def test_parse_time_delta(unquoted_raw: str, expected: timedelta | type[Exception]):
    """Tests the various ways a time delta interval can be encoded (and the various ways it can fail)"""
    VALID_QUOTE_CHARS = ["'", '"']

    # Check weird edge cases from unquoted intervals or badly quoted intervals
    with pytest.raises(UnparseableVariableExpressionError):
        parse_time_delta(unquoted_raw)

    for quote_char in ["'", '"']:
        with pytest.raises(UnparseableVariableExpressionError):
            parse_time_delta(quote_char + unquoted_raw)
        with pytest.raises(UnparseableVariableExpressionError):
            parse_time_delta(unquoted_raw + quote_char)

    with pytest.raises(UnparseableVariableExpressionError):
        parse_time_delta(VALID_QUOTE_CHARS[0] + quote_char + VALID_QUOTE_CHARS[1])
    with pytest.raises(UnparseableVariableExpressionError):
        parse_time_delta(VALID_QUOTE_CHARS[1] + quote_char + VALID_QUOTE_CHARS[0])

    # Now do the actual test
    if isinstance(expected, type):
        for quote_char in VALID_QUOTE_CHARS:
            with pytest.raises(expected):
                parse_time_delta(quote_char + unquoted_raw + quote_char)
    else:
        for quote_char in VALID_QUOTE_CHARS:
            actual = parse_time_delta(quote_char + unquoted_raw + quote_char)
            assert isinstance(actual, timedelta)
            assert actual == expected, f"Input string: {quote_char + unquoted_raw + quote_char}"


@pytest.mark.parametrize(
    "var_body, expected",
    [
        ("1.23", Constant(1.23)),
        ("123", Constant(123)),
        ("  123  ", Constant(123)),
        ("'-4.56 hours'", Constant(timedelta(hours=-4.56))),
        ('"0.12 days"', Constant(timedelta(days=0.12))),
        (" \t  '-4.56 hours' \t  ", Constant(timedelta(hours=-4.56))),
        ("now", NamedVariable(NamedVariableType.NOW)),
        ("NOW", UnparseableVariableExpressionError),  # case sensitive
        ("setMaxW", NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W)),
        ("SETMAXW", UnparseableVariableExpressionError),  # case sensitive
        ("foo", UnparseableVariableExpressionError),  # unknown named variable
        (
            "0.5 * 0.2",
            Expression(OperationType.MULTIPLY, Constant(0.5), Constant(0.2)),
        ),
        (
            "0.5 * setMaxW",
            Expression(OperationType.MULTIPLY, Constant(0.5), NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W)),
        ),
        (
            "setMaxW / 2",
            Expression(OperationType.DIVIDE, NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W), Constant(2)),
        ),
        (
            "  now  -    '-12   minutes'  ",
            Expression(OperationType.SUBTRACT, NamedVariable(NamedVariableType.NOW), Constant(timedelta(minutes=-12))),
        ),
        (
            "now-'-12minutes'",
            Expression(OperationType.SUBTRACT, NamedVariable(NamedVariableType.NOW), Constant(timedelta(minutes=-12))),
        ),
        (
            'now + "3 day"',
            Expression(OperationType.ADD, NamedVariable(NamedVariableType.NOW), Constant(timedelta(days=3))),
        ),
        (
            '"3 day" < "5 day"',
            Expression(OperationType.LT, Constant(timedelta(days=3)), Constant(timedelta(days=5))),
        ),
        (
            "rtgMaxW / 2",
            Expression(OperationType.DIVIDE, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_W), Constant(2)),
        ),
        ("setMaxVA", NamedVariable(NamedVariableType.DERSETTING_SET_MAX_VA)),
        ("setMaxVar", NamedVariable(NamedVariableType.DERSETTING_SET_MAX_VAR)),
        ("setMaxVarNeg", NamedVariable(NamedVariableType.DERSETTING_SET_MAX_VAR_NEG)),
        ("setMaxChargeRateW", NamedVariable(NamedVariableType.DERSETTING_SET_MAX_CHARGE_RATE_W)),
        ("setMaxDischargeRateW", NamedVariable(NamedVariableType.DERSETTING_SET_MAX_DISCHARGE_RATE_W)),
        ("setMinPFOverExcited", NamedVariable(NamedVariableType.DERSETTING_SET_MIN_PF_OVER_EXCITED)),
        ("setMinPFUnderExcited", NamedVariable(NamedVariableType.DERSETTING_SET_MIN_PF_UNDER_EXCITED)),
        ("setMaxWh", NamedVariable(NamedVariableType.DERSETTING_SET_MAX_WH)),
        (
            "rtgMaxVar == 5.0",
            Expression(OperationType.EQ, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_VAR), Constant(5.0)),
        ),
        (
            "rtgMaxVarNeg == 5.0",
            Expression(OperationType.EQ, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_VAR_NEG), Constant(5.0)),
        ),
        (
            "rtgMaxW != 0.5",
            Expression(OperationType.NE, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_W), Constant(0.5)),
        ),
        (
            "rtgMaxChargeRateW <= 0.5",
            Expression(
                OperationType.LTE, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_CHARGE_RATE_W), Constant(0.5)
            ),
        ),
        (
            "rtgMaxDischargeRateW > 0.5",
            Expression(
                OperationType.GT, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_DISCHARGE_RATE_W), Constant(0.5)
            ),
        ),
        (
            "rtgMinPFOverExcited > 0.5",
            Expression(
                OperationType.GT, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MIN_PF_OVER_EXCITED), Constant(0.5)
            ),
        ),
        (
            "rtgMinPFUnderExcited <= 0.5",
            Expression(
                OperationType.LTE,
                NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MIN_PF_UNDER_EXCITED),
                Constant(0.5),
            ),
        ),
        (
            "rtgMaxWh >= 0.5",
            Expression(OperationType.GTE, NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_WH), Constant(0.5)),
        ),
        ("now + foo", UnparseableVariableExpressionError),
        ("now foo +", UnparseableVariableExpressionError),
        ("now foo ", UnparseableVariableExpressionError),
        ("7 + + 8 ", UnparseableVariableExpressionError),
        ("'5 mins + now ", UnparseableVariableExpressionError),  # Unterminated string literal
        ("now + '5 mins", UnparseableVariableExpressionError),  # Unterminated string literal
        # Storage extension
        (
            "setMinWh >= 0.5",
            Expression(OperationType.GTE, NamedVariable(NamedVariableType.DERSETTING_SET_MIN_WH), Constant(0.5)),
        ),
        (
            "negRtgMaxChargeRateW + 50",
            Expression(
                OperationType.ADD,
                NamedVariable(NamedVariableType.DERCAPABILITY_NEG_RTG_MAX_CHARGE_RATE_W),
                Constant(50),
            ),
        ),
    ],
)
def test_parse_variable_expression_body(
    var_body: str, expected: type[Exception] | NamedVariable | Constant | Expression
):
    """Top level parsing test to ensure that a variety of variable bodies parse (or fail) in an expected fashion"""

    if isinstance(expected, type):
        with pytest.raises(expected):
            parse_variable_expression_body(var_body, None)
    else:
        actual = parse_variable_expression_body(var_body, None)
        assert isinstance(actual, NamedVariable) or isinstance(actual, Constant) or isinstance(actual, Expression)
        assert actual == expected, f"Input string: {var_body}"


@pytest.mark.parametrize(
    "var_body,expected,param_key",
    [
        (
            "this < rtgMaxVA",
            Expression(
                OperationType.LT,
                NamedVariable(NamedVariableType.DERSETTING_SET_MAX_VA),
                NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_VA),
            ),
            "setMaxVA",
        ),
        (
            "this < rtgMaxVA",
            UnparseableVariableExpressionError,
            "someUndefinedNamedVariable",
        ),
    ],
)
def test_parse_variable_expression_body_this(
    var_body: str, expected: type[Exception] | NamedVariable | Constant | Expression, param_key: str | None
) -> None:
    """Parsing to ensure that variable bodies that contain `this` parse (or fail) as expected"""
    if isinstance(expected, type):
        with pytest.raises(expected):
            parse_variable_expression_body(var_body, param_key)
    else:
        actual = parse_variable_expression_body(var_body, param_key)
        assert isinstance(actual, NamedVariable) or isinstance(actual, Constant) or isinstance(actual, Expression)
        assert actual == expected, f"Input string: {var_body}"


@pytest.mark.parametrize(
    "input, expected",
    [
        (None, False),
        ("", False),
        ("string value", False),
        (123, False),
        (1.23, False),
        (Decimal("1.2"), False),
        (datetime(2022, 11, 3), False),
        (timedelta(2), False),
        (Action("", {}), False),
        ([], False),
        ({}, False),
        (NamedVariable(NamedVariableType.NOW), True),
        (NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W), True),
        (Constant(1.23), True),
        (Constant(timedelta(5)), True),
        (Expression(OperationType.ADD, Constant(1.23), NamedVariable(NamedVariableType.NOW)), True),
    ],
)
def test_is_resolvable_variable(input: Any, expected: bool):
    result = is_resolvable_variable(input)
    assert isinstance(result, bool)
    assert result == expected


@pytest.mark.parametrize(
    "parameter,variable,expected",
    [
        (Constant(value=0), NamedVariableType.DERSETTING_SET_MAX_W, False),
        (Constant(value=5), NamedVariableType.DERSETTING_SET_MAX_W, False),
        (NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W), NamedVariableType.DERSETTING_SET_MAX_W, True),
        (NamedVariable(NamedVariableType.DERSETTING_SET_MAX_VA), NamedVariableType.DERSETTING_SET_MAX_W, False),
        (
            Expression(OperationType.ADD, Constant(1.23), NamedVariable(NamedVariableType.NOW)),
            NamedVariableType.DERSETTING_SET_MAX_W,
            False,
        ),
        (
            Expression(OperationType.ADD, NamedVariable(NamedVariableType.NOW), Constant(1.23)),
            NamedVariableType.DERSETTING_SET_MAX_W,
            False,
        ),
        (
            Expression(OperationType.ADD, Constant(1.23), NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W)),
            NamedVariableType.DERSETTING_SET_MAX_W,
            True,
        ),
        (
            Expression(OperationType.ADD, NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W), Constant(1.23)),
            NamedVariableType.DERSETTING_SET_MAX_W,
            True,
        ),
    ],
)
def test_has_named_variable(
    parameter: NamedVariable | Expression | Constant, variable: NamedVariableType, expected: bool
):
    result = has_named_variable(parameter_value=parameter, named_variable=variable)
    assert isinstance(result, bool)
    assert result == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        ("SET_MAX_W", "setMaxW"),
        ("SET_MAX_VAR", "setMaxVar"),
        ("NOW", "now"),
    ],
)
def test_snake_to_camel(input: str, expected: str) -> None:
    assert snake_to_camel(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (NamedVariableType.DERCAPABILITY_RTG_MAX_VAR, "DERCapability.rtgMaxVar"),
        (NamedVariableType.DERCAPABILITY_RTG_MAX_VAR_NEG, "DERCapability.rtgMaxVarNeg"),
        (NamedVariableType.DERSETTING_SET_MIN_WH, "DERSetting.setMinWh"),
        (NamedVariableType.DERCAPABILITY_RTG_MAX_VA, "DERCapability.rtgMaxVA"),
        (NamedVariableType.DERSETTING_SET_MAX_VA, "DERSetting.setMaxVA"),
        (NamedVariableType.DERCAPABILITY_NEG_RTG_MAX_CHARGE_RATE_W, "(-DERCapability.rtgMaxChargeRateW)"),
        (NamedVariableType.NOW, "now"),
    ],
)
def test_named_variable_repr(input: NamedVariableType, expected: str) -> None:
    assert named_variable_repr(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (OperationType.ADD, "+"),
        (OperationType.MULTIPLY, "*"),
        (OperationType.SUBTRACT, "-"),
        (OperationType.DIVIDE, "/"),
        (OperationType.EQ, "=="),
        (OperationType.GT, ">"),
        (OperationType.GTE, ">="),
        (OperationType.LT, "<"),
        (OperationType.LTE, "<="),
        (OperationType.NE, "!="),
    ],
)
def test_operation_repr(input: OperationType, expected: str) -> None:
    assert operation_repr(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (NamedVariable(variable=NamedVariableType.DERCAPABILITY_RTG_MAX_VA), "DERCapability.rtgMaxVA"),
        (
            Expression(OperationType.ADD, NamedVariable(NamedVariableType.DERSETTING_SET_MIN_WH), Constant(5.5)),
            "DERSetting.setMinWh + 5.5",
        ),
        (Constant(654.456), "654.456"),
    ],
)
def test_base_expression_expression_representation(input: BaseExpression, expected: str) -> None:
    assert input.expression_representation() == expected
