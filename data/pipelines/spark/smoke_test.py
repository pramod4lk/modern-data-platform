"""Milestone 2 check: Spark writes an Iceberg table through Polaris to Ceph; Trino should then read it.

After running, in Trino:
    SELECT * FROM iceberg.smoke.hello;
    SELECT * FROM iceberg.smoke."hello$snapshots";
"""

from common.config import spark_session

spark = spark_session("iceberg_smoke_test")
spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.smoke")
spark.sql("CREATE TABLE IF NOT EXISTS lakehouse.smoke.hello (id INT, message STRING) USING iceberg")
spark.sql("INSERT INTO lakehouse.smoke.hello VALUES (1, 'hello from spark'), (2, 'iceberg on ceph')")
spark.sql("SELECT * FROM lakehouse.smoke.hello").show()
spark.sql("SELECT snapshot_id, committed_at, operation FROM lakehouse.smoke.hello.snapshots").show(truncate=False)
spark.stop()
