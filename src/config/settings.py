from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    url: str
    vm_user: str
    vm_pass: str

    class Config:
        env_file = Path(__file__).parents[2] / ".env"


settings = Settings()
