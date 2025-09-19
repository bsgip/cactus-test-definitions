from enum import StrEnum, auto


class CSIPAusVersion(StrEnum):
    """The various version identifiers for CSIP-Aus. Used for distinguishing what tests are compatible with what
    released versions CSIP-Aus."""

    RELEASE_1_2 = "v1.2"
    BETA_1_3_STORAGE = "v1.3-beta/storage"


class CSIPAusResource(StrEnum):
    """Labels for each resource type that the server/client tests might reference. This is not designed to be
    an exhaustive list of all SEP2 / CSIP-Aus models - only the entities that might have tests applied to them."""

    DeviceCapability = auto()

    Time = auto()

    MirrorUsagePointListLink = auto()
    MirrorUsagePointList = auto()
    MirrorUsagePoint = auto()
    MirrorMeterReadingList = auto()
    MirrorMeterReading = auto()

    EndDeviceListLink = auto()
    EndDeviceList = auto()
    EndDevice = auto()

    FunctionSetAssignmentsListLink = auto()
    FunctionSetAssignmentsList = auto()
    FunctionSetAssignments = auto()

    DERProgramListLink = auto()
    DERProgramList = auto()
    DERProgram = auto()

    DERControlListLink = auto()
    DERControlList = auto()
    DERControl = auto()

    DefaultDERControlLink = auto()
    DefaultDERControl = auto()


class CSIPAusReadingLocation(StrEnum):
    Site = auto()  # The reading is measured at the site's connection point
    Device = auto()  # The reading is measured at the actual device (behind the meter)


class CSIPAusReadingType(StrEnum):
    """A non exhaustive set of CSIPAus reading types / role flags that can be specified in tests"""

    ActivePowerAverage = auto()
    ActivePowerInstantaneous = auto()
    ActivePowerMaximum = auto()
    ActivePowerMinimum = auto()

    ReactivePowerAverage = auto()
    ReactivePowerInstantaneous = auto()
    ReactivePowerMaximum = auto()
    ReactivePowerMinimum = auto()

    FrequencyAverage = auto()
    FrequencyInstantaneous = auto()
    FrequencyMaximum = auto()
    FrequencyMinimum = auto()

    VoltageSinglePhaseAverage = auto()
    VoltageSinglePhaseInstantaneous = auto()
    VoltageSinglePhaseMaximum = auto()
    VoltageSinglePhaseMinimum = auto()
