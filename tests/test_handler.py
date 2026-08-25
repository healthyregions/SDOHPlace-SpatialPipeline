import json

import pytest

from sdohplace_spatial.handler import STUB_ERROR_CODE, lambda_handler


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Bucket, Key, Body, ContentType=None):
        if isinstance(Body, str):
            Body = Body.encode("utf-8")
        self.objects[(Bucket, Key)] = {"Body": Body, "ContentType": ContentType}


def _event():
    return {
        "record_id": "herop-rsulgs",
        "s3_key": "uploads/herop-rsulgs/20260820T143022Z/dose_sys_counties.csv",
        "upload_kind": "csv",
        "boundary_year": 2018,
        "spatial_level": "county",
        "geo_id_column": "GEOID",
    }


def test_handler_writes_stub_result_json_next_to_upload():
    s3 = FakeS3()
    out = lambda_handler(_event(), None, s3_client=s3)

    key = "uploads/herop-rsulgs/20260820T143022Z/result.json"
    stored = s3.objects[("herop-sdohplace-upload", key)]
    body = json.loads(stored["Body"].decode("utf-8"))

    assert out["ok"] is False
    assert out["error_code"] == STUB_ERROR_CODE
    assert body == out
    assert body["record_id"] == "herop-rsulgs"
    assert "geometry" not in body
    assert stored["ContentType"] == "application/json"


def test_handler_uses_uploads_bucket_env(monkeypatch):
    monkeypatch.setenv("UPLOADS_BUCKET", "test-bucket")
    s3 = FakeS3()
    lambda_handler(_event(), None, s3_client=s3)
    assert ("test-bucket", "uploads/herop-rsulgs/20260820T143022Z/result.json") in s3.objects


def test_handler_missing_s3_key_does_not_write():
    s3 = FakeS3()
    with pytest.raises(ValueError, match="invalid payload"):
        lambda_handler({"record_id": "herop-rsulgs"}, None, s3_client=s3)
    assert s3.objects == {}
