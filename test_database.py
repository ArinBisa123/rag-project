from sqlalchemy import text
from sources.database.connection import engine
from sources.database.query.get_employee import get_employee
from sources.database.query.get_employee_claim import get_employee_claim
from sources.database.query.get_total_claim import get_total_claim



try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DB_NAME()"))
        print("connected database:",result.scalar())

except Exception as e:
    print(type(e).__name__,e)


employee = get_employee('EMP0008')
print(employee)
claims = get_employee_claim('EMP0008')
print(claims)
total = get_total_claim('EMP0008', 2026)
print(total)