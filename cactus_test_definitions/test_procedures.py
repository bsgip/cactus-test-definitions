from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

import yaml
import yaml_include
from cactus_test_definitions.actions import Action, validate_action_parameters
from cactus_test_definitions.errors import TestProcedureDefinitionError
from dataclass_wizard import YAMLWizard


class TestProcedureId(StrEnum):
    __test__ = False  # Prevent pytest from picking up this class
    ALL_01 = "ALL-01"
    ALL_02 = "ALL-02"


@dataclass
class Event:
    type: str
    parameters: dict


@dataclass
class Step:
    event: Event
    actions: list[Action]


@dataclass
class Preconditions:
    db: str


@dataclass
class TestProcedure:
    __test__ = False  # Prevent pytest from picking up this class
    description: str
    category: str
    classes: list[str]
    steps: dict[str, Step]
    envoy_environment_variables: dict[str, Any] | None = None
    preconditions: Preconditions | None = None


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

    def _validate_actions(self):
        """Validate actions of test procedure steps

        Ensure,
        - action has the correct parameters
        - if parameters refer to steps then those steps are defined for the test procedure
        """

        for test_procedure_name, test_procedure in self.test_procedures.items():
            for step_name, step in test_procedure.steps.items():
                for action in step.actions:
                    validate_action_parameters(test_procedure_name, step_name, action)

                    # Provide additional "action specific" validation
                    match action.type:
                        case "enable-listeners" | "remove-listeners":
                            for listener_step_name in action.parameters["listeners"]:
                                if listener_step_name not in test_procedure.steps.keys():
                                    raise TestProcedureDefinitionError(
                                        f"{test_procedure_name}.{step_name}. Refers to unknown step '{listener_step_name}'."  # noqa: E501
                                    )

    def validate(self):
        self._validate_actions()


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
