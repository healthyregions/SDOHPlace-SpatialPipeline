"""Lambda entry: S3 in → result.json out. CSV is still a stub; geo path is #6."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3

from sdohplace_spatial.errors import PipelineError
from sdohplace_spatial.geo import derive_geo
from sdohplace_spatial.keys import InvalidS3Key, result_key_from_s3_key

DEFAULT_BUCKET = "herop-sdohplace-upload"
STUB_ERROR_CODE = "not_implemented"
STUB_MESSAGE = (
    "Spatial derivation is not implemented yet for this upload_kind. "
    "The handler accepted the payload and wrote this stub so the manager can poll."
)


def _uploads_bucket() -> str:
    return os.environ.get("UPLOADS_BUCKET", DEFAULT_BUCKET)


def _s3_client(s3_client: Any | None) -> Any:
    if s3_client is not None:
        return s3_client
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
    return boto3.client("s3", region_name=region)


def stub_result(event: dict[str, Any]) -> dict[str, Any]:
    record_id = event.get("record_id")
    return {
        "ok": False,
        "error_code": STUB_ERROR_CODE,
        "message": STUB_MESSAGE,
        "record_id": record_id,
    }


def failure_result(error_code: str, message: str, record_id: Any = None) -> dict[str, Any]:
    body = {"ok": False, "error_code": error_code, "message": message}
    if record_id is not None:
        body["record_id"] = record_id
    return body


def write_result_json(s3_client: Any, bucket: str, result_key: str, body: dict[str, Any]) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=result_key,
        Body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def _s3_bytes(s3_client: Any, bucket: str, key: str) -> bytes:
    try:
        resp = s3_client.get_object(Bucket=bucket, Key=key)
        body = resp["Body"]
        return body.read() if hasattr(body, "read") else body
    except Exception as exc:
        raise PipelineError("unreadable_file", f"Could not read s3://{bucket}/{key}: {exc}") from exc


def derive_result(event: dict[str, Any], s3_client: Any, bucket: str) -> dict[str, Any]:
    kind = event.get("upload_kind")
    if kind == "geo":
        raw = _s3_bytes(s3_client, bucket, event["s3_key"])
        body = derive_geo(raw, event["s3_key"])
        if event.get("record_id") is not None:
            body["record_id"] = event.get("record_id")
        return body
    return stub_result(event)


def lambda_handler(event: dict[str, Any] | None, context: Any, s3_client: Any | None = None) -> dict[str, Any]:
    """Direct async invoke payload (no API Gateway wrapper)."""
    event = event if isinstance(event, dict) else {}
    bucket = _uploads_bucket()
    client = _s3_client(s3_client)

    try:
        result_key = result_key_from_s3_key(event.get("s3_key"))
    except InvalidS3Key as exc:
        raise ValueError(f"invalid payload: {exc}") from exc

    try:
        body = derive_result(event, client, bucket)
    except PipelineError as exc:
        body = failure_result(exc.error_code, exc.message, event.get("record_id"))

    write_result_json(client, bucket, result_key, body)
    return body
