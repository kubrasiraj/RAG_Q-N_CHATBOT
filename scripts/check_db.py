from sqlalchemy import text

from app.db.session import engine


def check_database_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))

            print("Database connection successful!")
            print(result.scalar())

    except Exception as error:
        print("Database connection failed!")
        print(error)

    finally:
        engine.dispose()


if __name__ == "__main__":
    check_database_connection()