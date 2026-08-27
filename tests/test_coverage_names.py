from sdohplace_spatial.coverage_names import spatial_coverage_from_matches
from sdohplace_spatial.states import CONUS_FIPS, NATIONAL_FIPS


def test_coverage_one_state_from_county_id():
    assert spatial_coverage_from_matches({"050US17019"}, "county") == ["Illinois"]


def test_coverage_two_states_sorted():
    ids = {"050US17019", "050US18097"}
    assert spatial_coverage_from_matches(ids, "county") == ["Illinois", "Indiana"]


def test_coverage_united_states_when_all_national_fips():
    ids = {f"050US{fp}001" for fp in NATIONAL_FIPS}
    out = spatial_coverage_from_matches(ids, "county")
    assert out[-1] == "United States"
    assert "Illinois" in out
    assert "Alaska" in out
    assert "Contiguous US" not in out


def test_coverage_contiguous_us_without_ak_hi():
    ids = {f"050US{fp}001" for fp in CONUS_FIPS}
    out = spatial_coverage_from_matches(ids, "county")
    assert out[-1] == "Contiguous US"
    assert "Alaska" not in out
    assert "Hawaii" not in out
    assert "United States" not in out
