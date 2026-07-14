import pymysql

def get_db_connection():
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='ban_hang',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn
