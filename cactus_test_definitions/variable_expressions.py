import tokenize
import abc
from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum, auto
from io import StringIO
from re import match, search
from typing import Any

from cactus_test_definitions.errors import UnparseableVariableExpressionError

ConstantType = timedelta | int | float


@dataclass
class Token:
    """Custom token implementaion

    Attributes:
        string: representation of original token from input
        type: the kind of token found, an enum directly related from tokenize
        line: the input line that the token belongs
        start: coordinates of the token start wrt input
        end: coordinates of the token end wrt input
        param_key: optional to help with the special case of backfilling a self reference (i.e $this)
            to its underlying named value
    """

    string: str
    type: int
    line: str
    start: tuple[int, int]
    end: tuple[int, int]
    param_key: str | None = None

    @staticmethod
    def from_token_info(token_info: tokenize.TokenInfo, param_key: str | None = None) -> "Token":
        """Takes a tokenize.TokenInfo and returns an internal Token"""
        return Token(
            string=token_info.string,
            type=token_info.type,
            line=token_info.line,
            start=token_info.start,
            end=token_info.start,
            param_key=param_key,
        )


class NamedVariableType(IntEnum):
    # MUST resolve to a tz aware representation of the current datetime
    # Referenced in a test definition as $(now)
    NOW = auto()

    # MUST resolve to the "DERSetting.setMaxW" of the current EndDevice under test. Value in Watts
    # Referenced in a test definition as $(setMaxW)
    DERSETTING_SET_MAX_W = auto()
    DERSETTING_SET_MAX_VA = auto()
    DERSETTING_SET_MAX_VAR = auto()
    DERSETTING_SET_MAX_CHARGE_RATE_W = auto()
    DERSETTING_SET_MAX_DISCHARGE_RATE_W = auto()
    DERSETTING_SET_MAX_WH = auto()

    # Must resolve to DERCapablity of the current EndDevice under test
    DERCAPABILITY_RTG_MAX_VA = auto()  # VA ( after multiplier applied), reference $rtgMaxVA
    DERCAPABILITY_RTG_MAX_VAR = auto()  # VAr ( atfer multiplier applied), reference $rtgMaxVar
    DERCAPABILITY_RTG_MAX_W = auto()  # W ( after multiplier applied), reference $rtgMaxW
    DERCAPABILITY_RTG_MAX_CHARGE_RATE_W = auto()  # W ( after multiiplier applied), reference $rtgMaxChargeRateW
    DERCAPABILITY_RTG_MAX_DISCHARGE_RATE_W = auto()  # W ( after multiplier applied), reference $rtgMaxDischargeRateW
    DERCAPABILITY_RTG_MAX_WH = auto()  # Wh ( after multiplier applied), reference $rtgMaxWh

    # Storage extension
    DERSETTING_SET_MIN_WH = auto()
    DERCAPABILITY_NEG_RTG_MAX_CHARGE_RATE_W = auto()  # -W (after multiplier applied), reference $negRtgMaxChargeRateW


class OperationType(IntEnum):
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()


OPERATION_MAPPINGS = {
    "+": OperationType.ADD,
    "-": OperationType.SUBTRACT,
    "*": OperationType.MULTIPLY,
    "/": OperationType.DIVIDE,
    "==": OperationType.EQ,
    "!=": OperationType.NE,
    "<": OperationType.LT,
    "<=": OperationType.LTE,
    ">": OperationType.GT,
    ">=": OperationType.GTE,
}


def snake_to_camel(snake: str) -> str:
    """Simple snake to camel case converter"""
    temp = snake.replace("_", " ").title().replace(" ", "")
    return temp[0].lower() + temp[1:]


def named_variable_repr(named_var: NamedVariableType) -> str:
    """Takes named variable enum and turns its name into its recognisable 2030.5 form"""
    name = named_var.name
    if len(name.split("_")) == 1:
        return snake_to_camel(name)
    match name.split("_", 1):
        case ["DERCAPABILITY", "NEG_RTG_MAX_CHARGE_RATE_W"]:
            return "(-DERCapability.rtgMaxChargeRateW)"
        case ["DERCAPABILITY", "RTG_MAX_VA"]:
            return "DERCapability.rtgMaxVA"
        case ["DERSETTING", "SET_MAX_VA"]:
            return "DERSetting.setMaxVA"
        case ["DERCAPABILITY", param_name]:
            return f"DERCapability.{snake_to_camel(param_name)}"
        case ["DERSETTING", param_name]:
            return f"DERSetting.{snake_to_camel(param_name)}"

    return snake_to_camel(name)


def operation_repr(op: OperationType) -> str:
    """Takes an operation type and returns its string representation"""
    operation_type_to_str_map: dict[OperationType, str] = {v: k for k, v in OPERATION_MAPPINGS.items()}
    return operation_type_to_str_map[op]


class BaseExpression(abc.ABC):
    """A base class for all expressions to inherit from"""

    @abc.abstractmethod
    def expression_representation(self) -> str:
        """Method for representing an expression human readably without overriding magic methods"""
        raise NotImplementedError


@dataclass
class Constant(BaseExpression):
    """Represents a constant value that doesn't require any test execution time resolution"""

    value: ConstantType  # The parsed value

    def expression_representation(self) -> str:
        return f"{self.value}"


@dataclass
class NamedVariable(BaseExpression):
    """A "NamedVariable" is value that can only be resolved at point during a test procedure execution (eg: as a
    Step's action is being applied). There are a fixed set of known variable types defined by NamedVariableType.

    Failures during resolving a variable (eg database doesn't have the data) MUST raise an exception
    """

    variable: NamedVariableType

    def expression_representation(self) -> str:
        return named_variable_repr(self.variable)


@dataclass
class Expression(BaseExpression):
    """An expression is a simple combination of two values that combine to make a single constant value. The operands
    can be constants or NamedVariables."""

    operation: OperationType
    lhs_operand: NamedVariable | Constant  # left hand side operand
    rhs_operand: NamedVariable | Constant  # right hand side operand

    def expression_representation(self) -> str:
        return " ".join(
            [
                f"{self.lhs_operand.expression_representation()}",
                f"{operation_repr(self.operation)}",
                f"{self.rhs_operand.expression_representation()}",
            ]
        )


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


def parse_unary_expression(token: Token) -> Constant | NamedVariable:
    """Parses a unary expression from a variable body"""

    if token.type == tokenize.NAME:
        # expect that a variable name is properly defined with correct case
        match token.string:
            case "now":
                return NamedVariable(NamedVariableType.NOW)
            case "this":
                if token.param_key == "this" or token.param_key is None:
                    raise UnparseableVariableExpressionError(f"$this cannot resolve to parameter {token.param_key}")
                # Modify token and maintain all other original data
                token.string = token.param_key
                token.param_key = None
                return parse_unary_expression(token)
            case "setMaxW":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MAX_W)
            case "setMaxVA":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MAX_VA)
            case "setMaxVar":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MAX_VAR)
            case "setMaxChargeRateW":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MAX_CHARGE_RATE_W)
            case "setMaxDischargeRateW":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MAX_DISCHARGE_RATE_W)
            case "setMaxWh":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MAX_WH)
            case "rtgMaxVA":
                return NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_VA)
            case "rtgMaxVar":
                return NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_VAR)
            case "rtgMaxW":
                return NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_W)
            case "rtgMaxChargeRateW":
                return NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_CHARGE_RATE_W)
            case "rtgMaxDischargeRateW":
                return NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_DISCHARGE_RATE_W)
            case "rtgMaxWh":
                return NamedVariable(NamedVariableType.DERCAPABILITY_RTG_MAX_WH)
            # Storage extension
            case "setMinWh":
                return NamedVariable(NamedVariableType.DERSETTING_SET_MIN_WH)
            case "negRtgMaxChargeRateW":
                return NamedVariable(NamedVariableType.DERCAPABILITY_NEG_RTG_MAX_CHARGE_RATE_W)

        raise UnparseableVariableExpressionError(f"'{token.string}' isn't recognized as a named variable")

    try:
        if token.type == tokenize.NUMBER:
            if "." in token.string:
                return Constant(float(token.string))
            else:
                return Constant(int(token.string))
    except ValueError:
        raise UnparseableVariableExpressionError(f"'{token.string}' can't be converted to a number")

    if token.type == tokenize.STRING:
        return Constant(parse_time_delta(token.string))

    raise UnparseableVariableExpressionError(f"Unable to parse token {token}")


def parse_binary_expression(lhs_token: Token, operation: Token, rhs_token: Token) -> Expression:

    if operation.type != tokenize.OP:
        raise UnparseableVariableExpressionError(f"Expected an operation (eg + - / *) but found {operation}")

    operation_type = OPERATION_MAPPINGS.get(operation.string, None)
    if operation_type is None:
        raise UnparseableVariableExpressionError(f"Unable to parse operator {operation.string} into a OperationType")

    lhs = parse_unary_expression(lhs_token)
    rhs = parse_unary_expression(rhs_token)

    return Expression(operation=operation_type, lhs_operand=lhs, rhs_operand=rhs)


def parse_variable_expression_body(var_body: str, param_key: str | None) -> NamedVariable | Expression | Constant:
    """Given a variable definition: $(now - '5 seconds') - this function should be passed contents of that variable
    definition (the string within the parentheses) eg: "now - '5 seconds'

    Common variable patterns include,
    $(now) - Will return a tz aware datetime corresponding to the current moment in time
    $(now - '5 minute') - Same as above, but offset 5 minutes in the past
    $(0.5 * setMaxW) - 50% of the currently configured setMaxW for the current EndDevice

    Args:
        var_body: parseable expression
        param_key: the key that the expression body belongs e.g. setMaxW

    Returns:
        Parsed object

    Raises:
        UnparseableVariableExpressionError: on failed parsing attempt
    """
    if not var_body:
        raise UnparseableVariableExpressionError("var_body is empty/None")

    # Use the python parser to generate a simplified set of tokens representing the variable definition
    # Convert these into the internal representation of a Token
    try:
        var_tokens = [
            Token.from_token_info(t, param_key)
            for t in tokenize.generate_tokens(StringIO(var_body).readline)
            if t.type in {tokenize.NUMBER, tokenize.OP, tokenize.STRING, tokenize.NAME}
        ]
    except tokenize.TokenError as exc:
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


def has_named_variable(
    parameter_value: NamedVariable | Expression | Constant, named_variable: NamedVariableType
) -> bool:
    """Return True if the supplied named variable is used in the the parameter 'parameter_value'"""

    if isinstance(parameter_value, Constant):
        return False

    if isinstance(parameter_value, NamedVariable):
        return parameter_value.variable == named_variable

    if isinstance(parameter_value, Expression):
        if isinstance(parameter_value.lhs_operand, NamedVariable):
            if parameter_value.lhs_operand.variable == named_variable:
                return True
        if isinstance(parameter_value.rhs_operand, NamedVariable):
            if parameter_value.rhs_operand.variable == named_variable:
                return True
        return False
