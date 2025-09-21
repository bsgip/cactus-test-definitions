import pytest
from cactus_test_definitions.csipaus import (
    CSIPAusReadingLocation,
    CSIPAusReadingType,
    CSIPAusResource,
    is_list_resource,
)


@pytest.mark.parametrize("enum_val", CSIPAusResource)
def test_CSIPAusResource_name_matches_value(enum_val: CSIPAusResource):
    """We want case varying enum values (to match the values in CSIP Aus). This means we need to manage the names
    manually and ensures we don't end up with a bad copy paste"""
    assert enum_val.value == enum_val.name


@pytest.mark.parametrize("enum_val", CSIPAusReadingLocation)
def test_CSIPAusReadingLocation_name_matches_value(enum_val: CSIPAusReadingLocation):
    """We want case varying enum values (to match the values in CSIP Aus). This means we need to manage the names
    manually and ensures we don't end up with a bad copy paste"""
    assert enum_val.value == enum_val.name


@pytest.mark.parametrize("enum_val", CSIPAusReadingType)
def test_CSIPAusReadingType_name_matches_value(enum_val: CSIPAusReadingType):
    """We want case varying enum values (to match the values in CSIP Aus). This means we need to manage the names
    manually and ensures we don't end up with a bad copy paste"""
    assert enum_val.value == enum_val.name


@pytest.mark.parametrize(
    "resource, expected",
    [
        (CSIPAusResource.ConnectionPoint, False),
        (CSIPAusResource.DeviceCapability, False),
        (CSIPAusResource.DERSettings, False),
        (CSIPAusResource.EndDeviceList, True),
        (CSIPAusResource.EndDevice, False),
        (CSIPAusResource.DERList, True),
        (CSIPAusResource.DERProgramList, True),
        (CSIPAusResource.MirrorUsagePointList, True),
        (CSIPAusResource.DERControlList, True),
        (CSIPAusResource.DERControl, False),
    ],
)
def test_is_list_resource(resource: CSIPAusResource, expected: bool):
    actual = is_list_resource(resource)
    assert isinstance(actual, bool)
    assert actual is expected
