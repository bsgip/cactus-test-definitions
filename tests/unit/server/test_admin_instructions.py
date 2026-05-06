import pytest

from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.server.test_procedures import TestProcedureId, parse_test_procedure
from cactus_test_definitions.server.validate import validate_test_procedure
from cactus_test_definitions.variable_expressions import Expression

# Minimal valid YAML mirroring S-ALL-21 precondition, with admin_instructions added
S_ALL_21_WITH_ADMIN_INSTRUCTIONS = """
Description: Default Control - Import Limit
Category: Control
Classes:
 - A

TargetVersions:
 - v1.2

Preconditions:
  required_clients:
    - id: client

Steps:
  - id: (A) PRECONDITION
    repeat_until_pass: true
    client: client
    admin_instructions:
      - type: ensure-end-device
        parameters:
          registered: true
          has_der_list: true
      - type: create-default-der-control
        parameters:
          opModImpLimW: $(setMaxW * 0.3)
    action:
      type: discovery
      parameters:
        resources:
          - EndDevice
          - DERControlList
          - DER
          - DefaultDERControl
    checks:
      - type: end-device
        parameters:
          matches_client: true
      - type: default-der-control
        parameters:
          opModImpLimW: $(setMaxW * 0.3)
          minimum_count: 1
"""


def test_admin_instructions_parse_and_validate():
    tp = parse_test_procedure(S_ALL_21_WITH_ADMIN_INSTRUCTIONS)
    validate_test_procedure(tp, TestProcedureId.S_ALL_21)

    step = tp.steps[0]

    # Parsing succeeds and validates
    assert step.repeat_until_pass is True
    assert step.admin_instructions is not None
    assert len(step.admin_instructions) == 2

    # check types
    instruction_ensure, instruction_create = tp.steps[0].admin_instructions
    assert instruction_ensure.type == "ensure-end-device"
    assert instruction_ensure.parameters == {"registered": True, "has_der_list": True}
    assert instruction_create.type == "create-default-der-control"


def test_admin_instructions_variable_expression_parsed():
    """Variable expressions in admin_instruction parameters are resolved to Expression objects,
    matching the same behaviour as Action parameters."""
    tp = parse_test_procedure(S_ALL_21_WITH_ADMIN_INSTRUCTIONS)
    ai_create = tp.steps[0].admin_instructions[1]

    opmod = ai_create.parameters["opModImpLimW"]
    assert isinstance(opmod, Expression), "$(setMaxW * 0.3) should be parsed into an Expression"


def test_admin_instructions_missing_mandatory_param_raises():
    """Omitting a mandatory parameter (registered on ensure-end-device) raises TestProcedureDefinitionError."""
    yaml = """
Description: Test
Category: Control
Classes: [A]
TargetVersions: [v1.2]
Preconditions:
  required_clients:
    - id: client
Steps:
  - id: STEP
    repeat_until_pass: true
    admin_instructions:
      - type: ensure-end-device
    action:
      type: discovery
      parameters:
        resources: [EndDevice]
"""
    tp = parse_test_procedure(yaml)
    with pytest.raises(TestProcedureDefinitionError, match="missing mandatory parameter"):
        validate_test_procedure(tp, TestProcedureId.S_ALL_21)


def test_admin_instructions_unknown_client_ref_raises():
    """An admin_instruction.client that isn't in required_clients raises TestProcedureDefinitionError."""
    yaml = """
Description: Test
Category: Control
Classes: [A]
TargetVersions: [v1.2]
Preconditions:
  required_clients:
    - id: clientA
Steps:
  - id: STEP
    repeat_until_pass: true
    admin_instructions:
      - type: ensure-end-device
        client: clientB
        parameters:
          registered: true
    action:
      type: discovery
      parameters:
        resources: [EndDevice]
"""
    tp = parse_test_procedure(yaml)
    with pytest.raises(TestProcedureDefinitionError, match="clientB"):
        validate_test_procedure(tp, TestProcedureId.S_ALL_21)
