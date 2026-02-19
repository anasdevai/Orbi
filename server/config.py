from dataclasses import dataclass
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

@dataclass
class Settings:
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = 'https://openrouter.ai/api/v1'
    DEFAULT_MODEL: str = 'openrouter/free'
    PLANNER_MODEL: str = 'openrouter/free'
    DB_PATH: str = './browseragent.db'
    MAX_TODOS: int = 12
    MAX_REPLAN_ATTEMPTS: int = 2

    def __init__(self):
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError('OPENROUTER_API_KEY not set in .env')
        self.OPENROUTER_API_KEY = api_key

        # Override defaults with env vars if present
        self.OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', self.OPENROUTER_BASE_URL)
        self.DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', self.DEFAULT_MODEL)
        self.PLANNER_MODEL = os.getenv('PLANNER_MODEL', self.PLANNER_MODEL)
        self.DB_PATH = os.getenv('DB_PATH', self.DB_PATH)
        self.MAX_TODOS = int(os.getenv('MAX_TODOS', self.MAX_TODOS))
        self.MAX_REPLAN_ATTEMPTS = int(os.getenv('MAX_REPLAN_ATTEMPTS', self.MAX_REPLAN_ATTEMPTS))

# Instantiate settings at module level
settings = Settings()
