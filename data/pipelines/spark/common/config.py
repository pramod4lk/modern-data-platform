"""Spark session and S3 configuration for the lakehouse.

Environment variables (from Kubernetes Secrets s3-credentials and polaris-engine):
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY      Ceph S3 user
    POLARIS_CLIENT_ID, POLARIS_CLIENT_SECRET      Polaris principal
    S3_ENDPOINT     default http://192.168.1.203:8080   (pods cannot resolve VM hostnames)
    POLARIS_URI     default http://polaris.data-system.svc.cluster.local:8181/api/catalog

The Spark catalog is called "lakehouse". In Trino the same tables appear in catalog "iceberg":
    Spark: lakehouse.bronze.lcr_monthly   ==   Trino: iceberg.bronze.lcr_monthly
"""

from __future__ import annotations

import os

import boto3
from pyspark.sql import SparkSession

CATALOG = "lakehouse"
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://192.168.1.203:8080")
POLARIS_URI = os.environ.get("POLARIS_URI", "http://polaris.data-system.svc.cluster.local:8181/api/catalog")


def spark_session(app_name: str) -> SparkSession:
    cred = f"{os.environ['POLARIS_CLIENT_ID']}:{os.environ['POLARIS_CLIENT_SECRET']}"
    c = f"spark.sql.catalog.{CATALOG}"
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config(c, "org.apache.iceberg.spark.SparkCatalog")
        .config(f"{c}.type", "rest")
        .config(f"{c}.uri", POLARIS_URI)
        .config(f"{c}.warehouse", "lakehouse")
        .config(f"{c}.credential", cred)
        .config(f"{c}.scope", "PRINCIPAL_ROLE:ALL")
        .config(f"{c}.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config(f"{c}.s3.endpoint", S3_ENDPOINT)
        .config(f"{c}.s3.path-style-access", "true")
        .config(f"{c}.client.region", "us-east-1")
        .config("spark.sql.defaultCatalog", CATALOG)
        .config("spark.sql.session.timeZone", "Asia/Kuala_Lumpur")
        .getOrCreate()
    )


def s3_client():
    return boto3.client("s3", endpoint_url=S3_ENDPOINT, region_name="us-east-1")
