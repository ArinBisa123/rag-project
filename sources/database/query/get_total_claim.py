from sqlalchemy import text
from sources.database.connection import engine
from typing import Optional

def get_total_claim(employee_id, year: Optional[int]=None, claim_type: Optional[str] = None):
    conditions = ["EmployeeID= :employee_id"]
    parameters = {"employee_id": employee_id}
    if year is not None:
        conditions.append("Year(TransactionDate)= :year")
        parameters["year"]= year

    if claim_type:
        conditions.append("ClaimType LIKE :claim_type")
        parameters["claim_type"]=(f"{claim_type}")

    where_clause = " AND ".join(conditions)
    query = text(
        f"""
            SELECT COUNT(*) AS ClaimCount,
            COALESCE(
                SUM(AmountSubmitted), 0
            ) AS TotalClaim
            FROM dbo.MedicalClaim WHERE {where_clause}
        """
    )
    with engine.connect() as connection:
        row=connection.execute(query, parameters).mappings().first()
    return{
        "employee_id":employee_id,
        "year": year,
        "claim_type":claim_type,
        "claim_count":row["ClaimCount"],
        "total_amount":float(row["TotalAmount"] or 0)
    }