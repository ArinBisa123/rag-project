from sqlalchemy import text
from sources.database.connection import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DB_NAME()"))
        print("connected database:",result.scalar())

except Exception as e:
    print(type(e).__name__,e)