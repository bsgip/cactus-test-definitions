from dataclasses import dataclass
from enum import StrEnum
from importlib import resources

import yaml
from dataclass_wizard import LoadMeta, YAMLWizard

from cactus_test_definitions.client.actions import Action
from cactus_test_definitions.client.checks import Check
from cactus_test_definitions.client.events import Event
from cactus_test_definitions.csipaus import CSIPAusVersion
from cactus_test_definitions.schema import UniqueKeyLoader


class TestProcedureId(StrEnum):
    """The set of all available test ID's

    This should be kept in sync with the current set of client test procedures loaded from the procedures directory"""

    __test__ = False  # Prevent pytest from picking up this class

    ALL_02 = "ALL-02"

    # Plugfest Versioned Tests
    PF_11 = "PF-11"
    PF_13 = "PF-13"
    PF_21 = "PF-21"
    PF_23 = "PF-23"
    PF_26 = "PF-26"
    PF_30 = "PF-30"

    # Pricing extension
    PRC_02 = "PRC-02"


@dataclass
class Step:
    """A step is a part of the test procedure that waits for some form of event before running a set of actions.

    It's common for a step to activate other "steps" so that the state of the active test procedure can "evolve" in
    response to client behaviour

    Instructions are out-of-band operations that need performing during the step
    e.g. disconnect DER from grid, disable power consumption etc.
    """

    event: Event  # The event to act as a trigger
    actions: list[Action]  # The actions to execute when the trigger is met
    instructions: list[str] | None = None


@dataclass
class Preconditions:
    """Preconditions are run during the "initialization" state that precedes the start of a test. They typically
    allow for the setup of the test.

    Checks are also included to prevent a client from starting a test before they have correctly met preconditions

    Instructions are out-of-band operations that need performing at the start of the test procedure
    e.g. attach a load etc.

    If immediate_start is set to True - the "initialization" step will be progressed through immediately so that the
    client has no opportunity to interact with the server in this state. Any actions will still be executed. Do NOT
    utilise immediate_start with precondition checks.
    """

    init_actions: list[Action] | None = None  # To be executed as the runner starts (before anything can occur)
    immediate_start: bool = False  # If True - a test execution will have NO "pre-start" phase.
    actions: list[Action] | None = None  # To be executed as the test case "starts" (usually on request of client)
    checks: list[Check] | None = None  # Will prevent move from "init" state to "started" state of a test if any fail
    instructions: list[str] | None = None


@dataclass
class Criteria:
    """Criteria represent the final pass/fail analysis run after a TestProcedure completion. They can consider both
    the final state of the test system as well as the interactions that happened while it was running"""

    checks: list[Check] | None = None  # These should be run at test procedure finalization to determine pass/fail


@dataclass
class TestProcedure(YAMLWizard):
    """Top level object for collecting everything relevant to a single TestProcedure"""

    __test__ = False  # Prevent pytest from picking up this class
    description: str  # Metadata from test definitions
    category: str  # Metadata from test definitions
    classes: list[str]  # Metadata from test definitions
    target_versions: list[CSIPAusVersion]  # What version(s) of csip-aus is this test targeting?
    steps: dict[str, Step]
    preconditions: Preconditions | None = None  # These execute during "init" and setup the test for a valid start state
    criteria: Criteria | None = None  # How will success/failure of this procedure be determined?


LoadMeta(raise_on_unknown_json_key=True).bind_to(TestProcedure)


def parse_test_procedure(yaml_contents: str) -> TestProcedure:
    """Given a YAML string - parse a TestProcedure.

    This will ensure the YAML parser will use all the "strict" extensions to reduce the incidence of errors"""

    tp = TestProcedure.from_yaml(
        yaml_contents,
        decoder=yaml.load,  # type: ignore
        Loader=UniqueKeyLoader,
    )
    if isinstance(tp, list):
        raise ValueError("Expected a singleton - not a list")

    return tp


def get_yaml_contents(test_procedure_id: TestProcedureId) -> str:
    """Finds the YAML contents for the TestProcedure with the specified TestProcedureId"""
    yaml_resource = resources.files("cactus_test_definitions.client.procedures") / f"{test_procedure_id}.yaml"
    with resources.as_file(yaml_resource) as yaml_file:
        with open(yaml_file) as f:
            yaml_contents = f.read()
            return yaml_contents


def get_test_procedure(test_procedure_id: TestProcedureId) -> TestProcedure:
    """Gets the TestProcedure with the nominated ID by loading its definition from disk"""
    yaml_contents = get_yaml_contents(test_procedure_id)
    return parse_test_procedure(yaml_contents)


def get_all_test_procedures() -> dict[TestProcedureId, TestProcedure]:
    """Gets every TestProcedure, keyed by their TestProcedureId"""
    return {tp_id: get_test_procedure(tp_id) for tp_id in TestProcedureId}
