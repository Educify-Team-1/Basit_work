from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Student-Teacher Matching System"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Matching Configuration
    MAX_MATCHES: int = 3
    MIN_RATING: float = 0.0
    RATING_WEIGHT: float = 0.6
    AVAILABILITY_WEIGHT: float = 0.4
    
    # Data Configuration
    DATA_SOURCE: str = "local"  # local, api, database
    EXTERNAL_API_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
