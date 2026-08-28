import geopandas as gpd
from shapely.geometry import Polygon
import pytest

from sdohplace_spatial.csv_join import derive_csv
from sdohplace_spatial.errors import PipelineError
from sdohplace_spatial.highlight import encode_highlight_ids
from sdohplace_spatial.handler import lambda_handler
from sdohplace_spatial.levels import shapefile_url
from tests.test_handler import FakeS3

BOXES = {
    "050US17019": Polygon([(-88.4, 40.0), (-88.3, 40.0), (-88.3, 40.1), (-88.4, 40.1), (-88.4, 40.0)]),
    "050US17031": Polygon([(-88.2, 41.7), (-88.1, 41.7), (-88.1, 41.8), (-88.2, 41.8), (-88.2, 41.7)]),
    "050US17113": Polygon([(-89.0, 40.4), (-88.9, 40.4), (-88.9, 40.5), (-89.0, 40.5), (-89.0, 40.4)]),
    "050US17043": Polygon([(-88.1, 41.8), (-88.0, 41.8), (-88.0, 41.9), (-88.1, 41.9), (-88.1, 41.8)]),
}


def master_counties():
    ids = list(BOXES)
    return gpd.GeoDataFrame(
        {"HEROP_ID": ids},
        geometry=[BOXES[i] for i in ids],
        crs="EPSG:4326",
    )


def _csv(rows: str) -> bytes:
    return rows.encode("utf-8")


def test_highlight_all_match_uses_star():
    assert encode_highlight_ids("050US", ["050US1", "050US2"], {"050US1", "050US2"}) == ["050US*"]


def test_highlight_few_missing_uses_minus():
    master = ["a", "b", "c", "d"]
    assert encode_highlight_ids("050US", master, {"a", "b", "c"}) == ["-d"]


def test_highlight_many_missing_lists_matches():
    master = ["a", "b", "c", "d"]
    assert encode_highlight_ids("050US", master, {"a"}) == ["a"]


def test_csv_prefers_fips_and_partial_match():
    # 1 of 4 missing → minus filter
    raw = _csv("FIPS,GEOID\n17019,x\n17031,x\n17113,x\n")
    out = derive_csv(
        raw,
        {"spatial_level": "county", "boundary_year": 2018, "geo_id_column": "GEOID"},
        master_gdf=master_counties(),
    )
    assert out["ok"] is True
    assert out["highlight_ids"] == ["-050US17043"]
    assert out["diagnostics"]["matched"] == 3
    assert out["diagnostics"]["unmatched"] == 0
    assert out["spatial_coverage"] == ["Illinois"]
    assert "POLYGON" in out["geometry"] or "MULTIPOLYGON" in out["geometry"]


def test_csv_zfill_restores_leading_zeros():
    """Excel/int FIPS: CA 06037 → 6037, AL 01001 → 1001. Join is still string HEROP_ID."""
    master = gpd.GeoDataFrame(
        {"HEROP_ID": ["050US06037", "050US01001"]},
        geometry=[BOXES["050US17019"], BOXES["050US17031"]],
        crs="EPSG:4326",
    )
    raw = _csv("FIPS\n6037\n1001\n6037.0\n")
    out = derive_csv(raw, {"spatial_level": "county"}, master_gdf=master)
    assert out["ok"] is True
    assert out["diagnostics"]["matched"] == 3
    assert out["spatial_coverage"] == ["Alabama", "California"]


def test_csv_zero_matches():
    raw = _csv("FIPS\n99999\n")
    with pytest.raises(PipelineError) as exc:
        derive_csv(raw, {"spatial_level": "county"}, master_gdf=master_counties())
    assert exc.value.error_code == "no_matching_ids"


def test_csv_mixed_tract_and_county():
    raw = _csv("FIPS\n17019\n17019005900\n")
    with pytest.raises(PipelineError) as exc:
        derive_csv(raw, {"spatial_level": "county"}, master_gdf=master_counties())
    assert exc.value.error_code == "mixed_spatial_level"


def test_csv_no_id_column():
    raw = _csv("name\nIllinois\n")
    with pytest.raises(PipelineError) as exc:
        derive_csv(raw, {"spatial_level": "county"}, master_gdf=master_counties())
    assert exc.value.error_code == "no_id_column"


def test_csv_herop_id_column():
    raw = _csv("HEROP_ID\n050US17019\n050US17031\n050US17113\n050US17043\n")
    out = derive_csv(raw, {"spatial_level": "county"}, master_gdf=master_counties())
    assert out["highlight_ids"] == ["050US*"]
    assert out["diagnostics"]["match_rate"] == 1.0


def test_csv_blockgroup_alias_is_bg():
    raw = _csv("FIPS\n170190059002\n")
    master = gpd.GeoDataFrame(
        {"HEROP_ID": ["150US170190059002"]},
        geometry=[BOXES["050US17019"]],
        crs="EPSG:4326",
    )
    out = derive_csv(raw, {"spatial_level": "blockgroup"}, master_gdf=master)
    assert out["ok"] is True
    assert out["highlight_ids"] == ["150US*"]


def test_handler_csv_uses_injected_master(monkeypatch):
    monkeypatch.setattr("sdohplace_spatial.csv_join.load_oeps", lambda level, year: master_counties())
    s3 = FakeS3()
    key = "uploads/herop-rsulgs/20260820T143022Z/dose.csv"
    s3.put_object(Bucket="herop-sdohplace-upload", Key=key, Body=_csv("FIPS\n17019\n17031\n"))
    event = {
        "record_id": "herop-rsulgs",
        "s3_key": key,
        "upload_kind": "csv",
        "spatial_level": "county",
        "boundary_year": 2018,
    }
    out = lambda_handler(event, None, s3_client=s3)
    assert out["ok"] is True
    assert out["diagnostics"]["matched"] == 2
    stored = s3.objects[("herop-sdohplace-upload", "uploads/herop-rsulgs/20260820T143022Z/result.json")]
    assert b"not_implemented" not in stored["Body"]


def test_shapefile_url_2010_county():
    assert shapefile_url("county", 2010).endswith("oeps/county-2010-500k-shp.zip")


def test_csv_2010_geometry_empty_highlight_ids():
    raw = _csv("FIPS\n17019\n17031\n")
    out = derive_csv(
        raw,
        {"spatial_level": "county", "boundary_year": 2010},
        master_gdf=master_counties(),
    )
    assert out["ok"] is True
    assert out["highlight_ids"] == []
    assert out["diagnostics"]["boundary_year_used"] == 2010
    assert any("2018-only" in w for w in out["diagnostics"]["warnings"])
    assert "POLYGON" in out["geometry"] or "MULTIPOLYGON" in out["geometry"]


def test_csv_unsupported_vintage():
    raw = _csv("FIPS\n17019\n")
    with pytest.raises(PipelineError) as exc:
        derive_csv(raw, {"spatial_level": "county", "boundary_year": 2020}, master_gdf=master_counties())
    assert exc.value.error_code == "unsupported_vintage"


def test_handler_csv_2010_uses_injected_master(monkeypatch):
    monkeypatch.setattr(
        "sdohplace_spatial.csv_join.load_oeps",
        lambda level, year: master_counties(),
    )
    s3 = FakeS3()
    key = "uploads/herop-rsulgs/20260820T143022Z/dose.csv"
    s3.put_object(Bucket="herop-sdohplace-upload", Key=key, Body=_csv("FIPS\n17019\n"))
    event = {
        "record_id": "herop-rsulgs",
        "s3_key": key,
        "upload_kind": "csv",
        "spatial_level": "county",
        "boundary_year": 2010,
    }
    out = lambda_handler(event, None, s3_client=s3)
    assert out["ok"] is True
    assert out["highlight_ids"] == []
    assert out["diagnostics"]["boundary_year_used"] == 2010
