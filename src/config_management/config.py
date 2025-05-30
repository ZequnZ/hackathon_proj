from pydantic_settings import SettingsConfigDict

from config_management.config_settings import BasicSettings


class Settings(BasicSettings):
    # Overwrite the config table in pyproject.toml
    model_config = SettingsConfigDict(
        # Ingore unknown CLI arguments
        cli_ignore_unknown_args=True,
    )


class Config(Settings):
    def __init__(self, settings: Settings):
        super().__init__(settings)


config = Config(Settings())
print(config.model_dump())
