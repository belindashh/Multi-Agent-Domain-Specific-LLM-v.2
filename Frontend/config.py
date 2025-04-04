import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_MODEL = os.getenv("OPENAI_MODEL")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    DB_NAME = os.getenv("DB_NAME")
    CHAT_TB_NAME = os.getenv("CHAT_TB_NAME")
    DATA_TB_NAME = os.getenv("DATA_TB_NAME")
    MATH_TB_NAME = os.getenv("MATH_TB_NAME")
    TABLE_TB_NAME = os.getenv("TABLE_TB_NAME")
    SEARCH_TB_NAME = os.getenv("SEARCH_TB_NAME")
    SEARCHINFO_TB_NAME = os.getenv("SEARCHINFO_TB_NAME")