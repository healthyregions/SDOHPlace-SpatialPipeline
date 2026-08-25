from sdohplace_spatial.aardvark import centroid_lat_lon, envelope


def test_envelope_is_west_east_north_south():
    assert envelope(-88.3, -88.2, 40.1, 40.0) == "ENVELOPE(-88.300000,-88.200000,40.100000,40.000000)"


def test_centroid_is_lat_then_lon():
    assert centroid_lat_lon(-88.25, 40.05) == "40.050000,-88.250000"
