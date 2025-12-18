from dataclasses import dataclass
from enum import StrEnum
from importlib import resources

import yaml
from cactus_test_definitions.client.actions import Action
from cactus_test_definitions.client.checks import Check
from cactus_test_definitions.client.events import Event
from cactus_test_definitions.csipaus import CSIPAusVersion
from cactus_test_definitions.schema import UniqueKeyLoader
from dataclass_wizard import LoadMeta, YAMLWizard


class TestProcedureId(StrEnum):
    """The set of all available test ID's

    This should be kept in sync with the current set of client test procedures loaded from the procedures directory"""

    __test__ = False  # Prevent pytest from picking up this class
    ALL_01 = "ALL-01"
    ALL_02 = "ALL-02"
    ALL_03 = "ALL-03"
    ALL_03_REJ = "ALL-03-REJ"
    ALL_04 = "ALL-04"
    ALL_05 = "ALL-05"
    ALL_06 = "ALL-06"
    ALL_07 = "ALL-07"
    ALL_08 = "ALL-08"
    ALL_09 = "ALL-09"
    ALL_10 = "ALL-10"
    ALL_11 = "ALL-11"
    ALL_12 = "ALL-12"
    ALL_13 = "ALL-13"
    ALL_14 = "ALL-14"
    ALL_15 = "ALL-15"
    ALL_16 = "ALL-16"
    ALL_17 = "ALL-17"
    ALL_18 = "ALL-18"
    ALL_19 = "ALL-19"
    ALL_20 = "ALL-20"
    ALL_21 = "ALL-21"
    ALL_22 = "ALL-22"
    ALL_23 = "ALL-23"
    ALL_24 = "ALL-24"
    ALL_25 = "ALL-25"
    ALL_25_EXT = "ALL-25-EXT"
    ALL_26 = "ALL-26"
    ALL_27 = "ALL-27"
    ALL_28 = "ALL-28"
    ALL_29 = "ALL-29"
    ALL_30 = "ALL-30"
    DRA_01 = "DRA-01"
    DRA_02 = "DRA-02"
    DRD_01 = "DRD-01"
    DRL_01 = "DRL-01"
    DRG_01 = "DRG-01"
    GEN_01 = "GEN-01"
    GEN_02 = "GEN-02"
    GEN_03 = "GEN-03"
    GEN_04 = "GEN-04"
    GEN_05 = "GEN-05"
    GEN_06 = "GEN-06"
    GEN_07 = "GEN-07"
    GEN_08 = "GEN-08"
    GEN_09 = "GEN-09"
    GEN_10 = "GEN-10"
    GEN_11 = "GEN-11"
    GEN_12 = "GEN-12"
    GEN_13 = "GEN-13"
    LOA_01 = "LOA-01"
    LOA_02 = "LOA-02"
    LOA_03 = "LOA-03"
    LOA_04 = "LOA-04"
    LOA_05 = "LOA-05"
    LOA_06 = "LOA-06"
    LOA_07 = "LOA-07"
    LOA_08 = "LOA-08"
    LOA_09 = "LOA-09"
    LOA_10 = "LOA-10"
    LOA_11 = "LOA-11"
    LOA_12 = "LOA-12"
    LOA_13 = "LOA-13"
    MUL_01 = "MUL-01"
    MUL_02 = "MUL-02"
    MUL_03 = "MUL-03"

    # Storage extension
    BES_01 = "BES-01"
    BES_02 = "BES-02"
    BES_03 = "BES-03"
    BES_04 = "BES-04"


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

    return TestProcedure.from_yaml(
        yaml_contents,
        decoder=yaml.load,  # type: ignore
        Loader=UniqueKeyLoader,
    )


def get_yaml_contents(test_procedure_id: TestProcedureId) -> str:
    """Finds the YAML contents for the TestProcedure with the specified TestProcedureId"""
    yaml_resource = resources.files("cactus_test_definitions.client.procedures") / f"{test_procedure_id}.yaml"
    with resources.as_file(yaml_resource) as yaml_file:
        with open(yaml_file, "r") as f:
            yaml_contents = f.read()
            return yaml_contents


def get_test_procedure(test_procedure_id: TestProcedureId) -> TestProcedure:
    """Gets the TestProcedure with the nominated ID by loading its definition from disk"""
    yaml_contents = get_yaml_contents(test_procedure_id)
    return parse_test_procedure(yaml_contents)


def get_all_test_procedures() -> dict[TestProcedureId, TestProcedure]:
    """Gets every TestProcedure, keyed by their TestProcedureId"""
    return {tp_id: get_test_procedure(tp_id) for tp_id in TestProcedureId}
