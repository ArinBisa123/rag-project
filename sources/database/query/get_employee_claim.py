from sqlalchemy import text
from sources.database.connection import engine
from typing import Optional

def get_employee_claim(employee_id, year: Optional[int]=None, claim_type:Optional[str]=None, provider:Optional[str]=None):
   conditions=["EmployeeID = :employee_id"]
   parameters={"employee_id " :employee_id}

   if year is not None:
    conditions.append("Year(TransactionDate)= :year")
    parameters["year"]= year

   if claim_type:
    conditions.append("ClaimType LIKE :claim_type")
    parameters["claim_type"]=(f"{claim_type}")

   if provider:
    conditions.append("Provider LIKE :provider")
    parameters["provider"]=(f"{provider}")

   where_clause = " AND ".join(conditions)
   query = text(
        f"""
            SELECT * FROM dbo.MedicalClaim WHERE {where_clause} ORDER BY TransactionDate DESC
        """
    )
   with engine.connect() as connection:
        result = connection.execute(
            query,parameters
        )
        rows = result.mappings().all()
        return [
            dict(row) for row in rows
        ]