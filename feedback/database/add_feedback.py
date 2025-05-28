# file to store feedback in the database
from .db_config import get_db_connection
import json


# id:INTEGER, createdAt:TIMESTAMP, output:JSON, feedback:TEXT
def add_feedback(created_at: str, output: dict, feedback: str):
    """
    Adds feedback to the database.

    Args:
        createdAt (str): The timestamp when the feedback was created.
        output (dict): The output data associated with the feedback.
        feedback (str): The feedback text.

    Returns:
        bool: True if the feedback was added successfully, False otherwise.
    """
    conn = get_db_connection()
    print(f"Connecting to database: {conn}")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO feedback (created_at, output, feedback) VALUES (%s, %s, %s)",
            (created_at, json.dumps(output), feedback),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding feedback: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()
