# Spark image with Iceberg and S3 support + the POC's PySpark pipelines.
# Build from the repository root:
#   docker build -f images/spark/Dockerfile -t <registry>/poc-spark:0.1.0 .
# Check the Iceberg release notes for the newest version supporting your Spark version.
ARG SPARK_IMAGE=apache/spark:3.5.6-python3
FROM ${SPARK_IMAGE}

ARG ICEBERG_VERSION=1.9.2
ARG SCALA_VERSION=2.12
ARG SPARK_MINOR=3.5
ARG MAVEN=https://repo1.maven.org/maven2/org/apache/iceberg

USER root
RUN set -eux; \
    cd /opt/spark/jars; \
    curl -fsSLO ${MAVEN}/iceberg-spark-runtime-${SPARK_MINOR}_${SCALA_VERSION}/${ICEBERG_VERSION}/iceberg-spark-runtime-${SPARK_MINOR}_${SCALA_VERSION}-${ICEBERG_VERSION}.jar; \
    curl -fsSLO ${MAVEN}/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar

COPY images/spark/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY data/pipelines/spark /opt/poc/pipelines/spark
COPY data/quality /opt/poc/quality
COPY data/contracts /opt/poc/contracts
COPY data/reference /opt/poc/reference
ENV PYTHONPATH=/opt/poc/pipelines/spark

USER spark
