# Airflow image with the providers the POC needs. dbt runs in its own virtualenv to avoid dependency clashes.
# Build: docker build -f images/airflow/Dockerfile -t <registry>/poc-airflow:0.1.0 .
ARG AIRFLOW_IMAGE=apache/airflow:3.0.6-python3.12
FROM ${AIRFLOW_IMAGE}

COPY images/airflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

USER root
RUN python -m venv /opt/dbt-venv && /opt/dbt-venv/bin/pip install --no-cache-dir dbt-trino==1.9.0 \
    && chown -R airflow: /opt/dbt-venv
USER airflow
ENV PATH="/opt/dbt-venv/bin:${PATH}"

COPY --chown=airflow data/pipelines/dbt /opt/poc/dbt
RUN cp /opt/poc/dbt/profiles.yml.example /opt/poc/dbt/profiles.yml
