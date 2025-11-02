from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Iterable

import yaml
import yaml_include
from cactus_test_definitions.client.actions import Action, validate_action_parameters
from cactus_test_definitions.client.checks import Check, validate_check_parameters
from cactus_test_definitions.client.events import Event, validate_event_parameters
from cactus_test_definitions.csipaus import CSIPAusVersion
from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.schema import UniqueKeyLoader
from dataclass_wizard import YAMLWizard


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
    ALL_26 = "ALL-26"
    ALL_27 = "ALL-27"
    ALL_28 = "ALL-28"
    ALL_29 = "ALL-29"
    ALL_30 = "ALL-30"
    DRA_01 = "DRA-01"
    DRA_02 = "DRA-02"
    DRD_01 = "DRD-01"
    DRL_01 = "DRL-01"
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
    OPT_1_IN_BAND = "OPT-1-IN-BAND"
    OPT_1_OUT_OF_BAND = "OPT-1-OUT-OF-BAND"

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

    @staticmethod
    def get_yaml(test_procedure_id: str) -> str:
        yaml_resource = resources.files("cactus_test_definitions.client.procedures") / f"{test_procedure_id}.yaml"
        with resources.as_file(yaml_resource) as yaml_file:
            with open(yaml_file, "r") as f:
                yaml_contents = f.read()
                return yaml_contents


@dataclass
class TestProcedures(YAMLWizard):
    """Represents a collection of CSIP-AUS client test procedure descriptions/specifications

    By sub-classing the YAMLWizard mixin, we get access to the class method `from_yaml`
    which we can use to create an instances of `TestProcedures`.
    """

    __test__ = False  # Prevent pytest from picking up this class

    description: str
    version: str
    test_procedures: dict[str, TestProcedure]

    def _do_action_validate(self, procedure: TestProcedure, procedure_name: str, location: str, action: Action):
        """Handles the full validation of an action's definition for a parent procedure.

        procedure: The parent TestProcedure for action
        procedure_name: The name of procedure (used for labelling errors)
        location: Where in procedure can you find action? (used for labelling errors)
        action: The action to validate

        raises TestProcedureDefinitionError on failure
        """
        validate_action_parameters(procedure_name, location, action)

        # Provide additional "action specific" validation
        match action.type:
            case "enable-steps" | "remove-steps":
                for step_name in action.parameters["steps"]:
                    if step_name not in procedure.steps.keys():
                        raise TestProcedureDefinitionError(
                            f"{procedure_name}.{location}. Refers to unknown step '{step_name}'."
                        )

    def _validate_actions(self):
        """Validate actions of test procedure steps / preconditions

        Ensure,
        - action has the correct parameters
        - if parameters refer to steps then those steps are defined for the test procedure
        """

        for test_procedure_name, test_procedure in self.test_procedures.items():
            # Validate actions in the preconditions
            if test_procedure.preconditions:
                if test_procedure.preconditions.actions:
                    for action in test_procedure.preconditions.actions:
                        self._do_action_validate(test_procedure, test_procedure_name, "Precondition", action)

                if test_procedure.preconditions.init_actions:
                    for action in test_procedure.preconditions.init_actions:
                        self._do_action_validate(test_procedure, test_procedure_name, "Precondition", action)

            # Validate actions that exist on steps
            for step_name, step in test_procedure.steps.items():
                for action in step.actions:
                    self._do_action_validate(test_procedure, test_procedure_name, step_name, action)

    def _validate_checks(self):
        """Validate checks of test procedures

        Ensure,
        - check has the correct parameters
        """

        for test_procedure_name, test_procedure in self.test_procedures.items():
            if test_procedure.criteria and test_procedure.criteria.checks:
                for check in test_procedure.criteria.checks:
                    validate_check_parameters(test_procedure_name, check)

    def _validate_events(self):
        """Validate events of test procedure steps

        Ensure,
        - event has the correct parameters
        """

        for test_procedure_name, test_procedure in self.test_procedures.items():
            for step_name, step in test_procedure.steps.items():
                validate_event_parameters(test_procedure_name, step_name, step.event)

    def validate(self):
        self._validate_actions()
        self._validate_checks()
        self._validate_events()


class TestProcedureConfig:
    __test__ = False  # Prevent pytest from picking up this class

    @staticmethod
    def from_yamlfile(path: Path, skip_validation: bool = False) -> TestProcedures:
        """Converts a yaml file given by 'path' into a 'TestProcedures' instance.

        Supports parts of the TestProcedures instance being described by external
        YAML files. These are referenced in the parent yaml file using the `!include` directive.

        skip_validation: If True, the test_procedures.validate() call will not be made

        Example:

            Description: CSIP-AUS Client Test Procedures
            Version: 0.1
            TestProcedures:
              ALL-01: !include ALL-01.yaml
        """
        with open(path, "r") as f:
            yaml_contents = f.read()

        # Modifies the pyyaml's load method to support references to external yaml files
        # through the `!include` directive.
        yaml.add_constructor(
            "!include", constructor=yaml_include.Constructor(base_dir=path.parent), Loader=UniqueKeyLoader
        )

        # ...because we are using YAMLWizard we need to supply a decoder and a Loader to
        # use this modified version.
        test_procedures: TestProcedures = TestProcedures.from_yaml(
            yaml_contents,
            decoder=yaml.load,  # type: ignore
            Loader=UniqueKeyLoader,
        )

        if not skip_validation:
            test_procedures.validate()

        return test_procedures

    @staticmethod
    def from_resource() -> TestProcedures:
        yaml_resource = resources.files("cactus_test_definitions.client.procedures") / "test-procedures.yaml"
        with resources.as_file(yaml_resource) as yaml_file:
            return TestProcedureConfig.from_yamlfile(path=yaml_file)

    @staticmethod
    def available_tests() -> Iterable[str]:
        test_procedures: TestProcedures = TestProcedureConfig.from_resource()
        return test_procedures.test_procedures.keys()
