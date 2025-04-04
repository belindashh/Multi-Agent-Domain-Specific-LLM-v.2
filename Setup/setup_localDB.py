import mysql.connector 
from config import Config
from dotenv import load_dotenv
load_dotenv()

DB_name = Config.DB_NAME 
Chat_TB = Config.CHAT_TB_NAME
Data_TB = Config.DATA_TB_NAME
Math_TB = Config.MATH_TB_NAME
Table_TB = Config.TABLE_TB_NAME
Search_TB = Config.SEARCH_TB_NAME
SearchInfo_TB = Config.SEARCHINFO_TB_NAME

conn = mysql.connector.connect(user='root',  
        password='',  
        host='localhost') 

cursor = conn.cursor()

cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_name}")
cursor.execute(f"USE {DB_name}")

# cursor.execute(f"DROP TABLE IF EXISTS {Data_TB}")
cursor.execute(f"DROP TABLE IF EXISTS {Chat_TB}")

cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {Chat_TB} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cursor.execute(f"DROP TABLE IF EXISTS {Math_TB}")

cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {Math_TB} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cursor.execute(f"DROP TABLE IF EXISTS {Table_TB}")

cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {Table_TB} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cursor.execute(f"DROP TABLE IF EXISTS {Search_TB}")

cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {Search_TB} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cursor.execute(f"DROP TABLE IF EXISTS {SearchInfo_TB}")

cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SearchInfo_TB} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {Data_TB} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255),
    title TEXT,
    description TEXT,
    abstract TEXT,
    abstract_embed JSON,
    abstract_bigrams TEXT,
    abstract_bigram_embed JSON,
    content TEXT,
    content_embed JSON,
    content_bigrams TEXT,
    content_bigram_embed JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
cursor.execute(create_table_sql)

print("Database and Tables Data_DB, Chat_DB, Math_DB, Table_DB, Search_DB and SearchInfo_DB Created Successfully!")

cursor.close()
conn.close()