import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

# Path-style URLs (http://host/<bucket>/<key>) let the gateway/Ingress route by bucket path
# without rewriting it, which would break the SigV4 signature of presigned URLs.
_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    connect_timeout=3,
    read_timeout=10,
    retries={"max_attempts": 2},
)


def client(endpoint: str, access_key: str, secret_key: str) -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=_CONFIG,
    )


def ensure_buckets(s3: BaseClient, *buckets: str) -> None:
    for bucket in buckets:
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError:
            try:
                s3.create_bucket(Bucket=bucket)
            except ClientError as e:
                if e.response["Error"]["Code"] not in (
                    "BucketAlreadyOwnedByYou",
                    "BucketAlreadyExists",
                ):
                    raise
