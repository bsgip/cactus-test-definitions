from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Iterable

import yaml
import yaml_include
from cactus_test_definitions.actions import Action, validate_action_parameters
from cactus_test_definitions.checks import Check, validate_check_parameters
from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.events import Event, validate_event_parameters
from dataclass_wizard import YAMLWizard


class TestProcedureId(StrEnum):
    """The set of all available test ID's

    This should be kept in sync with the current set of test procedures loaded from the procedures directory"""

    __test__ = False  # Prevent pytest from picking up this class
    ALL_01 = "ALL-01"
    ALL_02 = "ALL-02"
    ALL_03 = "ALL-03"
    ALL_04 = "ALL-04"
    ALL_05 = "ALL-05"
    ALL_06 = "ALL-06"
    ALL_07 = "ALL-07"
    ALL_08 = "ALL-08"
    ALL_09 = "ALL-09"
    ALL_10 = "ALL-10"
    ALL_11 = "ALL-11"
    GEN_01 = "GEN-01"
    GEN_02 = "GEN-02"
    LOA_01 = "LOA-01"
    LOA_02 = "LOA-02"
    OPT_1_IN_BAND = "OPT-1-IN-BAND"
    OPT_1_OUT_OF_BAND = "OPT-1-OUT-OF-BAND"


@dataclass
class Step:
    """A step is a part of the test procedure that waits for some form of event before running a set of actions.

    It's common for a step to activate other "steps" so that the state of the active test procedure can "evolve" in
    response to client behaviour"""

    event: Event  # The event to act as a trigger
    actions: list[Action]  # The actions to execute when the trigger is met


@dataclass
class Preconditions:
    """Preconditions are run during the "initialization" state that precedes the start of a test. They typically
    allow for the setup of the test.

    Checks are also included to prevent a client from starting a test before they have correctly met preconditions"""

    actions: list[Action] | None = None  # To be executed as the test case first "starts"
    checks: list[Check] | None = None  # Will prevent move from "init" state to "started" state of a test if any fail


@dataclass
class Criteria:
    """Criteria represent the final pass/fail analysis run after a TestProcedure completion. They can consider both
    the final state of the test system as well as the interactions that happened while it was running"""

    checks: list[Check] | None = None  # These should be run at test procedure finalization to determine pass/fail


@dataclass
class TestProcedure:
    """Top level object for collecting everything relevant to a single TestProcedure"""

    __test__ = False  # Prevent pytest from picking up this class
    description: str  # Metadata from test definitions
    category: str  # Metadata from test definitions
    classes: list[str]  # Metadata from test definitions
    steps: dict[str, Step]
    preconditions: Preconditions | None = None  # These execute during "init" and setup the test for a valid start state
    criteria: Criteria | None = None  # How will success/failure of this procedure be determined?


@dataclass
class TestProcedures(YAMLWizard):
    """Represents a collection of CSIP-AUS test procedure descriptions/specifications

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
            if test_procedure.preconditions and test_procedure.preconditions.actions:
                for action in test_procedure.preconditions.actions:
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
        yaml.add_constructor("!include", yaml_include.Constructor(base_dir=path.parent))

        # ...because we are using YAMLWizard we need to supply a decoder and a Loader to
        # use this modified version.
        test_procedures: TestProcedures = TestProcedures.from_yaml(yaml_contents, decoder=yaml.load, Loader=yaml.Loader)  # type: ignore # noqa: E501

        if not skip_validation:
            test_procedures.validate()

        return test_procedures

    @staticmethod
    def from_resource() -> TestProcedures:
        yaml_resource = resources.files("cactus_test_definitions.procedures") / "test-procedures.yaml"
        with resources.as_file(yaml_resource) as yaml_file:
            return TestProcedureConfig.from_yamlfile(path=yaml_file)

    @staticmethod
    def available_tests() -> Iterable[str]:
        test_procedures: TestProcedures = TestProcedureConfig.from_resource()
        return test_procedures.test_procedures.keys()
