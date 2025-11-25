from dataclasses import dataclass
from enum import StrEnum
from importlib import resources

import yaml
from cactus_test_definitions.csipaus import CSIPAusVersion
from cactus_test_definitions.schema import UniqueKeyLoader
from cactus_test_definitions.server.actions import Action
from cactus_test_definitions.server.checks import Check
from dataclass_wizard import LoadMeta, YAMLWizard


class TestProcedureId(StrEnum):
    """The set of all available test ID's

    This should be kept in sync with the current set of test procedures loaded from the procedures directory"""

    __test__ = False  # Prevent pytest from picking up this class
    S_ALL_01 = "S-ALL-01"
    S_ALL_02 = "S-ALL-02"
    S_ALL_03 = "S-ALL-03"
    S_ALL_04 = "S-ALL-04"
    S_ALL_05 = "S-ALL-05"
    S_ALL_25 = "S-ALL-25"
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
class TestProcedure(YAMLWizard):
    """Top level object for collecting everything relevant to a single TestProcedure"""

    __test__ = False  # Prevent pytest from picking up this class
    description: str  # Metadata from test definitions
    category: str  # Metadata from test definitions
    classes: list[str]  # Metadata from test definitions
    target_versions: list[CSIPAusVersion]  # What version(s) of csip-aus is this test targeting?
    preconditions: Preconditions
    steps: list[Step]  # What behavior will the test procedure be evaluating?


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
    yaml_resource = resources.files("cactus_test_definitions.server.procedures") / f"{test_procedure_id}.yaml"
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
