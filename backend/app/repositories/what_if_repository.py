"""Persistence for saved what-if analysis scenarios."""

import json
from datetime import datetime, timezone
from typing import Any

from app.models.what_if import WhatIfScenario


class WhatIfRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def create(
        self,
        analysis_type: str,
        name: str,
        input_data: dict[str, Any],
        result: dict[str, Any],
    ) -> WhatIfScenario:
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO what_if_scenarios
                    (analysis_type, name, input_json, result_json, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    analysis_type,
                    name,
                    json.dumps(input_data),
                    json.dumps(result),
                    created_at,
                ),
            )
            scenario_id = int(cursor.lastrowid)
            self.connection.commit()
            return WhatIfScenario(
                scenario_id=scenario_id,
                analysis_type=analysis_type,
                name=name,
                input_data=input_data,
                result=result,
                created_at=created_at,
            )
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def recent(self, limit: int = 50) -> list[WhatIfScenario]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT scenario_id, analysis_type, name, input_json,
                       result_json, created_at
                FROM what_if_scenarios
                ORDER BY created_at DESC, scenario_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [self._model(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get(self, scenario_id: int) -> WhatIfScenario | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT scenario_id, analysis_type, name, input_json,
                       result_json, created_at
                FROM what_if_scenarios
                WHERE scenario_id = %s
                """,
                (scenario_id,),
            )
            row = cursor.fetchone()
            return self._model(row) if row else None
        finally:
            cursor.close()

    @staticmethod
    def _model(row: dict[str, Any]) -> WhatIfScenario:
        return WhatIfScenario(
            scenario_id=row["scenario_id"],
            analysis_type=row["analysis_type"],
            name=row["name"],
            input_data=json.loads(row["input_json"]),
            result=json.loads(row["result_json"]),
            created_at=row["created_at"],
        )
