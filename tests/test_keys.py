import pytest

from sdohplace_spatial.keys import InvalidS3Key, result_key_from_s3_key


def test_result_key_from_job_folder_file():
    assert (
        result_key_from_s3_key(
            "uploads/herop-rsulgs/20260820T143022Z/dose_sys_counties.csv"
        )
        == "uploads/herop-rsulgs/20260820T143022Z/result.json"
    )


def test_result_key_strips_leading_slash():
    assert (
        result_key_from_s3_key(
            "/uploads/herop-rsulgs/20260820T143022Z/file.geojson"
        )
        == "uploads/herop-rsulgs/20260820T143022Z/result.json"
    )


def test_result_key_rejects_folder_and_empty():
    with pytest.raises(InvalidS3Key):
        result_key_from_s3_key("")
    with pytest.raises(InvalidS3Key):
        result_key_from_s3_key("uploads/herop-rsulgs/20260820T143022Z/")
    with pytest.raises(InvalidS3Key):
        result_key_from_s3_key(None)
