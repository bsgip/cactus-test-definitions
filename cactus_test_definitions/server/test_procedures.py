from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Iterable

import yaml
import yaml_include
from cactus_test_definitions.csipaus import CSIPAusVersion
from cactus_test_definitions.errors import TestProcedureDefinitionError
from cactus_test_definitions.schema import UniqueKeyLoader
from cactus_test_definitions.server.actions import Action, validate_action_parameters
from cactus_test_definitions.server.checks import Check, validate_check_parameters
from dataclass_wizard import YAMLWizard


class TestProcedureId(StrEnum):
    """The set of all available test ID's

    This should be kept in sync with the current set of test procedures loaded from the procedures directory"""

    __test__ = False  # Prevent pytest from picking up this class
    S_ALL_01 = "S-ALL-01"
    S_ALL_02 = "S-ALL-02"
    S_ALL_03 = "S-ALL-03"
    S_ALL_04 = "S-ALL-04"
    S_ALL_05 = "S-ALL-05"
    S_OPT_01 = "S-OPT-01"
    S_OPT_02 = "S-OPT-02"
    S_OPT_03 = "S-OPT-03"
    S_OPT_04 = "S-OPT-04"


class ClientType(StrEnum):
    DEVICE = "device"  # This is a direct device client - i.e. the cert will match a SPECIFIC EndDevice
    AGGREGATOR = "aggregator"  # This is an aggregator client - i.e. the cert can manage MANY EndDevices


@dataclass
class RequiredClient:
    """A RequiredClient is a way for a test to assert that it needs a specific client type or set of clients. The id
    will be used internally within a test to reference a specific client"""

    id: str  # How this client will be referred to within the step's of the test
    client_type: ClientType | None = None  # If set - the client type that is required


@dataclass
class Step:
    """A step is an action for a client to execute and then a series of checks to validate the results. If the action
    raises an exception OR any of the checks fail, this step will marked as failed and the test will be aborted.

    Actions might represent a single operation or they may represent a series of polls/checks over a period of time.
    """

    id: str  # Descriptive identifier for this step (must be unique)
    action: Action  # The action to execute when the step starts
    client: str | None = None  # The RequiredClient.id that will execute this step. If None - use the 0th client.
    use_client_context: str | None = (
        None  # Specify to allow a request to execute with clientX using the context of clientY
    )
    checks: list[Check] | None = None  # The checks (if any) to execute AFTER action completes to determine success
    instructions: list[str] | None = None  # Text to display while this step executes

    repeat_until_pass: bool = False  # If True - failing checks will cause this step to re-execute until successful


@dataclass
class Preconditions:
    """Preconditions are a way of setting up the test / server before the test begins.

    Instructions are out-of-band information to show until the preconditions are all met.

    If any checks are required - they will be polled regularly until ALL pass. For each check poll, a discovery
    will be run to ensure data is available.
    """

    required_clients: list[RequiredClient]  # What client(s) need to be supplied to run this test procedure


@dataclass
class TestProcedure:
    """Top level object for collecting everything relevant to a single TestProcedure"""

    __test__ = False  # Prevent pytest from picking up this class
    description: str  # Metadata from test definitions
    category: str  # Metadata from test definitions
    classes: list[str]  # Metadata from test definitions
    target_versions: list[CSIPAusVersion]  # What version(s) of csip-aus is this test targeting?
    preconditions: Preconditions
    steps: list[Step]  # What behavior will the test procedure be evaluating?


@dataclass
class TestProcedures(YAMLWizard):
    """Represents a collection of CSIP-AUS server test procedure descriptions/specifications

    By sub-classing the YAMLWizard mixin, we get access to the class method `from_yaml`
    which we can use to create an instances of `TestProcedures`.
    """

    __test__ = False  # Prevent pytest from picking up this class

    description: str
    version: str
    test_procedures: dict[str, TestProcedure]

    def validate(self):
        for tp_name, tp in self.test_procedures.items():

            # Check preconditions
            if not tp.preconditions.required_clients:
                raise TestProcedureDefinitionError(
                    f"{tp_name} has no RequiredClients element. At least 1 entry required"
                )
            required_clients_by_id = dict(((rc.id, rc) for rc in tp.preconditions.required_clients))

            for step in tp.steps:
                validate_action_parameters(tp_name, step.id, step.action)

                # Validate step checks
                if step.checks:
                    for check in step.checks:
                        validate_check_parameters(tp_name, check)

                # Ensure client exists
                if step.client is not None and step.client not in required_clients_by_id:
                    raise TestProcedureDefinitionError(
                        f"{tp_name} reference client {step.client} that isn't listed in RequiredClients."
                    )


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
        yaml_resource = resources.files("cactus_test_definitions.server.procedures") / "test-procedures.yaml"
        with resources.as_file(yaml_resource) as yaml_file:
            return TestProcedureConfig.from_yamlfile(path=yaml_file)

    @staticmethod
    def available_tests() -> Iterable[str]:
        test_procedures: TestProcedures = TestProcedureConfig.from_resource()
        return test_procedures.test_procedures.keys()
