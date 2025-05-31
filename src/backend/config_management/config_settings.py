import os
import sys
from pathlib import Path

from pydantic import (
    Field,
)
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def get_cli_parse_args() -> bool | None:
    """
    Based on the CLI arguments, return whether to parse the CLI arguments or not:
    - If the program is invoked by pytest, return None.
    - Otherwise, return True.
    """
    if sys.argv[0].split("/")[-1] == "pytest":
        # Program was invoked by pytest.
        return None
    else:
        # ref: https://github.com/pydantic/pydantic-settings/blob/7e7ccdbc7b27d3f3d292d35a3b5033ef740fd6f7/pydantic_settings/sources.py#L1017-L1018
        return True


class PyprojectTomlDefaultConfigSettingsSource(PyprojectTomlConfigSettingsSource):
    """
    Configuration setting here to set the [config.default] as the default table in pyproject.toml
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        toml_file: Path | None = None,
    ) -> None:
        self.toml_file_path = self._pick_pyproject_toml_file(
            toml_file, settings_cls.model_config.get("pyproject_toml_depth", 0)
        )
        # Set the default table here, default is [config.default]
        self.toml_table_header: tuple[str, ...] = settings_cls.model_config.get(
            "pyproject_toml_default_table_header", ("config", "default")
        )
        self.toml_data = self._read_files(self.toml_file_path)
        for key in self.toml_table_header:
            self.toml_data = self.toml_data.get(key, {})
        super(TomlConfigSettingsSource, self).__init__(settings_cls, self.toml_data)


class SourceSettings(BaseSettings):
    """
    SourceSettings class: define the sources and priorities for configuration.
    """

    environment: str = Field(
        default="local", alias="ENVIRONMENT", description="Development environment"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Orders of sources show the priority of the sources, the earlier the higher priority.
        return (
            CliSettingsSource(settings_cls, cli_parse_args=get_cli_parse_args()),
            env_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
            PyprojectTomlDefaultConfigSettingsSource(settings_cls),
        )


# "ENVIRONMENT" needs to be set in the environment variables to load the righe table.
# if os.environ.get("ENVIRONMENT") is None:
#     raise ValueError("ENVIRONMENT variable is not set")


class BasicSettings(SourceSettings):
    """
    BasicSettings class: define the environment-specific table in pyproject.toml.
    """

    model_config = SettingsConfigDict(
        pyproject_toml_table_header=(
            "config",
            os.environ.get("ENVIRONMENT"),
        ),
        pyproject_toml_default_table_header=("config", "default"),
        extra="ignore",
    )
