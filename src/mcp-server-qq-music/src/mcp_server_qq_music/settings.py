from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    storage_state_path: str = Field(default="~/.mcp/qq-music/state.json")


settings = Settings()
