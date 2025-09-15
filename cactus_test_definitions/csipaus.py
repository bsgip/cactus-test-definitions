from enum import StrEnum


class CSIPAusVersion(StrEnum):
    """The various version identifiers for CSIP-Aus. Used for distinguishing what tests are compatible with what
    released versions CSIP-Aus."""

    RELEASE_1_2 = "v1.2"
    BETA_1_3_STORAGE = "v1.3-beta/storage"
