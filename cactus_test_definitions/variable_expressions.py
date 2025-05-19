from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum, auto
from io import StringIO
from re import match, search
from tokenize import NAME, NUMBER, OP, STRING, TokenError, TokenInfo, generate_tokens
from typing import Any

from cactus_test_definitions.errors import UnparseableVariableExpressionError

ConstantType = timedelta | int | float


class NamedVariableType(IntEnum):
    # MUST resolve to a tz aware representation of the current datetime
    # Referenced in a test definition as $(now)
    NOW = auto()

    # MUST resolve to the "DERSetting.setMaxW" of the current EndDevice under test. Value in Watts
    # Referenced in a test definition as $(setMaxW)
    DERSETTING_SET_MAX_W = auto()


class OperationType(IntEnum):
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()


OPERATION_MAPPINGS = {
    "+": OperationType.ADD,
    "-": OperationType.SUBTRACT,
    "*": OperationType.MULTIPLY,
    "/": OperationType.DIVIDE,
}


@dataclass
class Constant:
    """Represents a constant value that doesn't require any test execution time resolution"""

    value: ConstantType  # The parsed value


@dataclass
class NamedVariable:
    """A "NamedVariable" is value that can only be resolved at point during a test procedure execution (eg: as a
    listener action is being applied). There are a fixed set of known variable types defined by NamedVariableType.

    Failures during resolving a variable (eg database doesn't have the data) MUST raise an exception
    """

    variable: NamedVariableType


@dataclass
class Expression:
    """An expression is a simple combination of two values that combine to make a single constant value. The operands
    can be constants or NamedVariables."""

    operation: OperationType
    lhs_operand: NamedVariable | Constant  # left hand side operand
    rhs_operand: NamedVariable | Constant  # right hand side operand


def parse_time_delta(var_body: str) -> timedelta:
    """Parses a string like '5 minutes' into a representative timedelta"""

    m = match(r"(['\"])([0-9\-\.]*)\s*([^']*)(['\"])", var_body)
    if m is None:
        raise UnparseableVariableExpressionError(f"{var_body} can't be parsed into a timedelta")

    open_quote = m.group(1)
    number_string = m.group(2)
    time_unit_string = m.group(3).lower()
    close_quote = m.group(4)

    if open_quote != close_quote:
        raise UnparseableVariableExpressionError(f"{var_body} can't be parsed into a timedelta. Mismatching quotes")

    try:
        number = float(number_string)
    except ValueError:
        raise UnparseableVariableExpressionError(
            f"{var_body} can't be parsed into a timedelta. Bad number {number_string}"
        )

    if time_unit_string in {"day", "days"}:
        return timedelta(days=number)
    elif time_unit_string in {"hour", "hours", "hrs", "hr"}:
        return timedelta(hours=number)
    elif time_unit_string in {"minute", "minutes", "min", "mins"}:
        return timedelta(minutes=number)
    elif time_unit_string in {"second", "seconds", "sec", "secs"}:
        return timedelta(seconds=number)
    else:
        raise UnparseableVariableExpressionError(
            f"{var_body} can't be parsed into a timedelta. Unknown unit {time_unit_string}"
        )


def parse_unary_expression(token: TokenInfo) -> Constant | NamedVariable:
    """Parses a unary expression from a variable body"""

    if token.type == NAME:
        match token.string.lower():
            case "now":
                return NamedVariable(NamedVariableType.NOW)
            case "setmaxw":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W)

        raise UnparseableVariableExpressionError(f"'{token.string}' isn't recognized as a named variable")

    try:
        if token.type == NUMBER:
            if "." in token.string:
                return Constant(float(token.string))
            else:
                return Constant(int(token.string))
    except ValueError:
        raise UnparseableVariableExpressionError(f"'{token.string}' can't be converted to a number")

    if token.type == STRING:
        return Constant(parse_time_delta(token.string))

    raise UnparseableVariableExpressionError(f"Unable to parse token {token}")


def parse_binary_expression(lhs_token: TokenInfo, operation: TokenInfo, rhs_token: TokenInfo) -> Expression:

    if operation.type != OP:
        raise UnparseableVariableExpressionError(f"Expected an operation (eg + - / *) but found {operation}")

    operation_type = OPERATION_MAPPINGS.get(operation.string, None)
    if operation_type is None:
        raise UnparseableVariableExpressionError(f"Unable to parse operator {operation.string} into a OperationType")

    lhs = parse_unary_expression(lhs_token)
    rhs = parse_unary_expression(rhs_token)

    return Expression(operation=operation_type, lhs_operand=lhs, rhs_operand=rhs)


def parse_variable_expression_body(var_body: str) -> NamedVariable | Expression | Constant:
    """Given a variable definition: $(now - '5 seconds') - this function should be passed contents of that variable
    definition (the string within the parentheses) eg: "now - '5 seconds'

    returns a parsed NamedVariable or Expression or raises UnparseableVariableExpressionError otherwise

    Cheat sheet of common variable patterns:

    $(now) - Will return a tz aware datetime corresponding to the current moment in time
    $(now - '5 minute') - Same as above, but offset 5 minutes in the past
    $(0.5 * DERSetting.setMaxW) - 50% of the currently configured setMaxW for the current EndDevice
    """
    if not var_body:
        raise UnparseableVariableExpressionError("var_body is empty/None")

    # Use the python parser to generate a simplified set of tokens representing the variable definition
    try:

        var_tokens = [t for t in generate_tokens(StringIO(var_body).readline) if t.type in {NUMBER, OP, STRING, NAME}]
    except TokenError as exc:
        raise UnparseableVariableExpressionError(f"Error tokenizing '{var_body}': {exc}")

    if len(var_tokens) == 1:
        return parse_unary_expression(var_tokens[0])
    elif len(var_tokens) == 3:
        return parse_binary_expression(var_tokens[0], var_tokens[1], var_tokens[2])
    else:
        raise UnparseableVariableExpressionError(f"Unable to parse {var_body} into a simple binary/unary expression")


def try_extract_variable_expression(body: Any) -> str | None:
    """Checks to see if a variable body (of any type) can be parsed by parse_variable_expression_body. If it can,
    it will be returned as a string. Otherwise None will be returned

    Can raise ValueError if body is a string appearing to contain a variable expression that is malformed (eg
    mismatching parentheses)"""
    if not isinstance(body, str):
        return None

    begin_variable_defn = body.find("$")
    if begin_variable_defn < 0:
        return None

    # The $ variable definition can be escaped with \$ so ensure it is checked
    if begin_variable_defn > 0 and (body[begin_variable_defn - 1] == "\\"):
        return None

    # At this point we are definitely parsing a variable expression. Failures here will raise ValueError
    if begin_variable_defn >= (len(body) - 1):
        raise ValueError(f"'{body}' appears to be a malformed variable definition. Try escaping $ like '\\$'")

    start_expr_body: int
    end_expr_body: int
    end_variable_defn: int  # First character after the end of the full variable definition
    if body[begin_variable_defn + 1] == "(":
        start_expr_body = begin_variable_defn + 2
        end_expr_body = body.index(")", start_expr_body)
        end_variable_defn = end_expr_body + 2
    else:
        start_expr_body = begin_variable_defn + 1

        remainder = body[start_expr_body:]
        match_variable = match(r"[_a-zA-Z0-9]*", remainder)
        if match_variable is None:
            raise ValueError(f"'{body}' appears to be a malformed variable definition")
        else:
            end_expr_body = start_expr_body + match_variable.end()
            end_variable_defn = end_expr_body + 1

    if start_expr_body == end_expr_body:
        raise ValueError(f"'{body}' appears to be a malformed variable definition.")
    variable_expression = body[start_expr_body:end_expr_body]

    # One last validation to look for leading/trailing text which would indicate
    leading_text = search(r"[^\s]", body[0:begin_variable_defn])
    if leading_text is not None:
        raise ValueError("Variable expressions must ONLY be a single variable with no other text")

    trailing_text = search(r"[^\s]", body[end_variable_defn:])
    if trailing_text is not None:
        raise ValueError("Variable expressions must ONLY be a single variable with no other text")

    return variable_expression


def is_resolvable_variable(v: Any) -> bool:
    """Returns True if the supplied value is a variable definition that requires resolving"""
    return isinstance(v, NamedVariable) or isinstance(v, Expression) or isinstance(v, Constant)
