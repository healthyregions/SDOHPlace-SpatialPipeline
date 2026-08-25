"""Lambda entry: read invoke payload, write stub result.json next to the upload.

Does not derive geometry. A fake success outline would recreate the Alaska bug.
Merge/dissolve is a later step; this stub lets the manager poll S3.
"""

from __future__ import annotations

import json
import os
from typing import Any

import boto3

from sdohplace_spatial.keys import InvalidS3Key, result_key_from_s3_key

DEFAULT_BUCKET = "herop-sdohplace-upload"
STUB_ERROR_CODE = "not_implemented"
STUB_MESSAGE = (
    "Spatial derivation is not implemented yet. "
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


def write_result_json(s3_client: Any, bucket: str, result_key: str, body: dict[str, Any]) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=result_key,
        Body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def lambda_handler(event: dict[str, Any] | None, context: Any, s3_client: Any | None = None) -> dict[str, Any]:
    """Direct async invoke payload (no API Gateway wrapper)."""
    event = event if isinstance(event, dict) else {}
    bucket = _uploads_bucket()
    client = _s3_client(s3_client)

    try:
        result_key = result_key_from_s3_key(event.get("s3_key"))
    except InvalidS3Key as exc:
        # Cannot write result.json without a job folder. Surface in CloudWatch only.
        raise ValueError(f"invalid payload: {exc}") from exc

    body = stub_result(event)
    write_result_json(client, bucket, result_key, body)
    return body
