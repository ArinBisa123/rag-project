from sqlalchemy import text
from sources.database.connection import engine
from typing import Optional

def get_employee(employee_id):
    query = text(
        """
        SELECT * FROM dbo.Employee WHERE EmployeeID = :employee_id
        """
    )
    with engine.connect() as connection:
        result = connection.execute(
            query, {
                "employee_id": employee_id
            }
        )
        row = result.mappings().first()
    return dict(row) if row else None