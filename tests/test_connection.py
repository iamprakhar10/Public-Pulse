from app.database.db import engine
print(engine,1390)

from sqlalchemy import text

def test_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        print("✅ Connected Successfully!")
        print(result.scalar())

if __name__ == "__main__":
    test_connection()