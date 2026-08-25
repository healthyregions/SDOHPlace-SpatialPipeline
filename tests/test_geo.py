import io
import json
import zipfile
from pathlib import Path

import pytest

geopandas = pytest.importorskip("geopandas")

from shapely.geometry import Polygon

from sdohplace_spatial.handler import lambda_handler
from tests.test_handler import FakeS3

BOX = Polygon([(-88.3, 40.0), (-88.2, 40.0), (-88.2, 40.1), (-88.3, 40.1), (-88.3, 40.0)])

GEOJSON = json.dumps(
    {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-88.3, 40.0],
                            [-88.2, 40.0],
                            [-88.2, 40.1],
                            [-88.3, 40.1],
                            [-88.3, 40.0],
                        ]
                    ],
                },
            }
        ],
    }
).encode("utf-8")


def _geo_event(filename: str = "box.geojson"):
    return {
        "record_id": "herop-geo",
        "s3_key": f"uploads/herop-geo/20260820T143022Z/{filename}",
        "upload_kind": "geo",
    }


def test_geojson_success_no_highlight_ids():
    s3 = FakeS3()
    event = _geo_event()
    s3.put_object(Bucket="herop-sdohplace-upload", Key=event["s3_key"], Body=GEOJSON)
    out = lambda_handler(event, None, s3_client=s3)

    result_key = "uploads/herop-geo/20260820T143022Z/result.json"
    stored = json.loads(s3.objects[("herop-sdohplace-upload", result_key)]["Body"])

    assert out["ok"] is True
    assert stored == out
    assert "POLYGON" in out["geometry"] or "MULTIPOLYGON" in out["geometry"]
    assert out["bounding_box"].startswith("ENVELOPE(")
    west, east, north, south = out["bounding_box"][9:-1].split(",")
    assert float(west) < float(east)
    assert float(south) < float(north)
    lat, lon = out["centroid"].split(",")
    assert 40.0 < float(lat) < 40.1
    assert -88.3 < float(lon) < -88.2
    assert out["highlight_ids"] == []
    assert out["spatial_coverage"] == []
    assert out["diagnostics"]["rows_in"] == 1


def test_kml_is_rejected():
    s3 = FakeS3()
    event = _geo_event("box.kml")
    s3.put_object(Bucket="herop-sdohplace-upload", Key=event["s3_key"], Body=b"<kml/>")
    out = lambda_handler(event, None, s3_client=s3)
    assert out["ok"] is False
    assert out["error_code"] == "unreadable_file"


def test_missing_upload_writes_unreadable_file():
    s3 = FakeS3()
    out = lambda_handler(_geo_event(), None, s3_client=s3)
    assert out["ok"] is False
    assert out["error_code"] == "unreadable_file"
    assert ("herop-sdohplace-upload", "uploads/herop-geo/20260820T143022Z/result.json") in s3.objects


def test_shapefile_zip_success(tmp_path: Path):
    gdf = geopandas.GeoDataFrame({"id": [1]}, geometry=[BOX], crs="EPSG:4326")
    shp_dir = tmp_path / "shp"
    shp_dir.mkdir()
    gdf.to_file(shp_dir / "box.shp")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in shp_dir.iterdir():
            zf.write(path, arcname=path.name)
    event = _geo_event("box.zip")
    s3 = FakeS3()
    s3.put_object(Bucket="herop-sdohplace-upload", Key=event["s3_key"], Body=buf.getvalue())
    out = lambda_handler(event, None, s3_client=s3)
    assert out["ok"] is True
    assert out["highlight_ids"] == []
