"""Long-running DBMS query collection worker."""

import time

import mysql.connector

from app.collectors.mysql_query_collector import MySQLQueryCollector
from app.config.database import get_connection
from app.config.settings import settings
from app.repositories.dbms_observation_repository import DBMSObservationRepository


def run(interval_seconds: int = 5, batch_size: int = 100) -> None:
    """Poll Performance Schema until interrupted and persist each batch."""

    connection = get_connection()
    collector = MySQLQueryCollector(connection)
    repository = DBMSObservationRepository(connection)
    print(
        f"[dbms-collector] polling every {interval_seconds}s; "
        f"batch size {batch_size}"
    )
    try:
        while True:
            try:
                observations = collector.poll(batch_size)
                persisted = repository.insert_many(observations)
                if persisted:
                    print(f"[dbms-collector] persisted {len(persisted)} observation(s)")
            except mysql.connector.Error as error:
                print(f"[dbms-collector] collection error; retrying: {error}")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n[dbms-collector] stopped")
    finally:
        connection.close()


if __name__ == "__main__":
    run(interval_seconds=getattr(settings, "dbms_collection_interval_seconds", 5))
