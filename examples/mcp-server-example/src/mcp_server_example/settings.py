from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    storage_state_path: str = Field(default="~/.mcp/example/state.json")


settings = Settings()
