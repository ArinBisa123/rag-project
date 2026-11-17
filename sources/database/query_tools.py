import json 
from datetime import date
from decimal import Decimal
from typing import Optional
from langchain_core.tools import tool
from sources.database.query.get_employee import get_employee
from sources.database.query.get_employee_claim import get_employee_claim
from sources.database.query.get_total_claim import get_total_claim

def json_serializer(value):
    if isinstance(value,(date,Decimal)):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

def to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2, default=json_serializer)

@tool
def find_employee(employee_id:Optional[str]=None, employee_name: Optional[str]=None)->str:
    """
    Get employee profile from SQL Server.

    Use this tool when the user asks about an employee's id, employee's name
    name, business unit, position, join date, or employment
    status and provides an Employee ID such as EMP0008.

    Do not invent an Employee ID.
    """

    employee = get_employee(employee_id=employee_id, employee_name=employee_name)
    if not employee:
        return(f"Employee {employee_id} was not found.")
    return to_json(employee)

@tool
def find_medical_claims(employee_id:str, 
                        year: Optional[int]= None,
                        claim_type: Optional [str] = None,
                        provider: Optional [str] = None,
                        ) -> str:
    """
        Search medical claim transactions for one employee.

        Use optional year, claim_type, and provider filters
        only when requested by the user.

        Examples:
        - Claim history for EMP0008
        - Dental claims for EMP0008 in 2026
        - Claims from a specific provider
    """
    claims = get_employee_claim(employee_id=employee_id.upper().strip(),
                                year=year,
                                claim_type=claim_type,
                                provider=provider
                                )
    if not claims:
        return("No matching medical claim transactions were found")
    return to_json(claims)

@tool
def get_medical_claim_total(employee_id:str,
                            year: Optional[int]=None, 
                            claim_type: Optional[str]= None) -> str:
    """
    Calculate medical claim count and total submitted
    amount for one employee.

    Use this tool for questions asking how many claims
    or the total claim amount. Year and claim type are
    optional filters.
    """
    result = get_total_claim(employee_id=employee_id.upper().strip(),
                             year=year,
                             claim_type=claim_type
                             )
    return to_json(result)

CLAIM_TOOLS =[
    find_employee, find_medical_claims, get_medical_claim_total
]