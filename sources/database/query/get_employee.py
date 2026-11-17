from sqlalchemy import text
from sources.database.connection import engine
from typing import Optional

def get_employee(employee_id: Optional[str]= None, employee_name: Optional[str]=None):
    if employee_id and employee_name:
        query = text(
            """
            SELECT * FROM dbo.Employee WHERE EmployeeID = :employee_id OR EmployeeName = :employee_name
            """
        )
        parameters = {
            "employee_id":employee_id.strip(),
            "employee_name":employee_name
        }
    elif employee_id:
        query = text(
                    """
                    SELECT * FROM dbo.Employee WHERE EmployeeID = :employee_id 
                    """
                )
        parameters = {
            "employee_id":employee_id.strip()
        }
    elif employee_name:
        query = text(
                            """
                            SELECT * FROM dbo.Employee WHERE EmployeeName = :employee_name 
                            """
                        )
        parameters = {
                    "employee_name":employee_name
                }
    else:
        return[]
    with engine.connect() as connection:
        result = connection.execute(
            query, parameters
        )
        row = result.mappings().all()
    return dict(row) if row else None