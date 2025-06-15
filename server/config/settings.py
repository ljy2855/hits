from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Environment settings
    ENV: str = os.getenv("ENV", "development")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    # GitHub OAuth settings
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET")
    
    @property
    def GITHUB_CALLBACK_URL(self) -> str:
        """환경에 따라 GitHub 콜백 URL을 동적으로 생성"""
        return f"{self.BASE_URL}/auth/github/callback"
    
    class Config:
        env_file = ".env"

settings = Settings() 