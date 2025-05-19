class TestProcedureDefinitionError(Exception):
    __test__ = False  # Prevent pytest from picking up this class


class UnresolvableVariableError(Exception):
    """Raised whenever a NamedVariable cannot be resolved at test execution time (eg: database doesn't have the
    requisite information)"""

    pass


class UnparseableVariableExpressionError(Exception):
    """Raised whenever a raw string cannot parse to a NamedVariable/Expression"""

    pass
