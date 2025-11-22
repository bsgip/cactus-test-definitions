from enum import StrEnum


class CSIPAusVersion(StrEnum):
    """The various version identifiers for CSIP-Aus. Used for distinguishing what tests are compatible with what
    released versions CSIP-Aus."""

    RELEASE_1_2 = "v1.2"
    BETA_1_3_STORAGE = "v1.3-beta/storage"


class CSIPAusResource(StrEnum):
    """Labels for each resource type that the server/client tests might reference. This is not designed to be
    an exhaustive list of all SEP2 / CSIP-Aus models - only the entities that might have tests applied to them."""

    DeviceCapability = "DeviceCapability"

    Time = "Time"

    MirrorUsagePointList = "MirrorUsagePointList"
    MirrorUsagePoint = "MirrorUsagePoint"

    EndDeviceList = "EndDeviceList"
    EndDevice = "EndDevice"
    ConnectionPoint = "ConnectionPoint"
    Registration = "Registration"

    FunctionSetAssignmentsList = "FunctionSetAssignmentsList"
    FunctionSetAssignments = "FunctionSetAssignments"

    DERProgramList = "DERProgramList"
    DERProgram = "DERProgram"

    DERControlList = "DERControlList"
    DERControl = "DERControl"

    DefaultDERControl = "DefaultDERControl"

    DERList = "DERList"
    DER = "DER"
    DERCapability = "DERCapability"
    DERSettings = "DERSettings"
    DERStatus = "DERStatus"

    SubscriptionList = "SubscriptionList"
    Subscription = "Subscription"

    Notification = "Notification"  # A Notification isn't normally discoverable - it's received via pub/sub webhook


class CSIPAusReadingLocation(StrEnum):
    Site = "Site"  # The reading is measured at the site's connection point
    Device = "Device"  # The reading is measured at the actual device (behind the meter)


class CSIPAusReadingType(StrEnum):
    """A non exhaustive set of CSIPAus reading types / role flags that can be specified in tests"""

    ActivePowerAverage = "ActivePowerAverage"
    ActivePowerInstantaneous = "ActivePowerInstantaneous"
    ActivePowerMaximum = "ActivePowerMaximum"
    ActivePowerMinimum = "ActivePowerMinimum"

    ReactivePowerAverage = "ReactivePowerAverage"
    ReactivePowerInstantaneous = "ReactivePowerInstantaneous"
    ReactivePowerMaximum = "ReactivePowerMaximum"
    ReactivePowerMinimum = "ReactivePowerMinimum"

    FrequencyAverage = "FrequencyAverage"
    FrequencyInstantaneous = "FrequencyInstantaneous"
    FrequencyMaximum = "FrequencyMaximum"
    FrequencyMinimum = "FrequencyMinimum"

    VoltageSinglePhaseAverage = "VoltageSinglePhaseAverage"
    VoltageSinglePhaseInstantaneous = "VoltageSinglePhaseInstantaneous"
    VoltageSinglePhaseMaximum = "VoltageSinglePhaseMaximum"
    VoltageSinglePhaseMinimum = "VoltageSinglePhaseMinimum"


def is_list_resource(resource: CSIPAusResource) -> bool:
    """Returns true if the specified resource is classified as a list resource (i.e. it supports list query params) and
    will return an entity with list attributes (eg 'all')"""
    return resource.name.endswith("List")  # This is a really simple method but it should work
