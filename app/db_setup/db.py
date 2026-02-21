import pyodbc
from src.config import settings

class SQLDB:
    def __init__(self):
        self.server = settings.DB_SERVER
        self.database = settings.DB_NAME
        self.username = settings.DB_USER
        self.password = settings.DB_PASSWORD
        self.driver = settings.DB_DRIVER
    
    def _get_db_connection(self):
        """
        Establishes a connection to the MSSQL Server using environment variables.
        """
        server = self.server
        database = self.database
        username = self.username
        password = self.password
        driver = self.driver

        conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    
        try:
            conn = pyodbc.connect(conn_str)
            return conn
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None


    def query_db(self, query):
        """
        Executes a query on the MSSQL Server.
        """
        conn = self._get_db_connection()
        columns, rows = [], []
        if conn is None:
            return {"columns": columns, "rows": rows}

        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    rows = [list(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error executing query: {e}")
        finally:
            conn.close()
        return {"columns": columns, "rows": rows}
        