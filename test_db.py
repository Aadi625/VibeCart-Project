from database import get_db_connection

conn = get_db_connection()

if conn:
    print("Connected Successfully")
else:
    print("Connection Failed")