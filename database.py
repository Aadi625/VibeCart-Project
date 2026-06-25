import mysql.connector
from mysql.connector import Error


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="bakhtani12",
            database="ecommerce_db"
        )

        return connection

    except Error as e:
        print("Database Connection Error:", e)
        return None