"""Derive the job-folder result.json key from the upload object key."""


class InvalidS3Key(ValueError):
    """s3_key is missing or cannot yield a sibling result.json."""


def result_key_from_s3_key(s3_key: str) -> str:
    """Return uploads/{record_id}/{timestamp}/result.json for a file in that folder.

    Example:
        uploads/herop-rsulgs/20260820T143022Z/dose_sys_counties.csv
        → uploads/herop-rsulgs/20260820T143022Z/result.json
    """
    if s3_key is None:
        raise InvalidS3Key("s3_key is required")
    key = str(s3_key).strip().lstrip("/")
    if not key or key.endswith("/"):
        raise InvalidS3Key("s3_key must be an object key, not a folder")
    folder, _filename = key.rsplit("/", 1) if "/" in key else ("", key)
    if not folder:
        return "result.json"
    return f"{folder}/result.json"
