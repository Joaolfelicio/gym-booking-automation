import os
import yaml
import logging
from azure.appconfiguration import AzureAppConfigurationClient
from azure.identity import DefaultAzureCredential
from .models import AppConfig, UserConfig, ClassConfig

class ConfigLoader:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_APP_CONFIG_ENDPOINT")
        self.local_config_path = "config.yaml"

    def load(self) -> AppConfig:
        if self.endpoint:
            logging.info(f"Loading configuration from Azure App Configuration endpoint: {self.endpoint}")
            return self._load_from_azure()
        elif os.path.exists(self.local_config_path):
            logging.info(f"Loading configuration from {self.local_config_path}.")
            return self._load_from_local()
        else:
            raise FileNotFoundError("No configuration source found (AZURE_APP_CONFIG_ENDPOINT or local config.yaml).")

    def _load_from_local(self) -> AppConfig:
        with open(self.local_config_path, "r") as f:
            data = yaml.safe_load(f)
        return AppConfig(**data)

    def _load_from_azure(self) -> AppConfig:
        credential = DefaultAzureCredential()
        client = AzureAppConfigurationClient(account_url=self.endpoint, credential=credential)
        
        # Fetching common settings
        app_id = client.get_configuration_setting(key="app_id").value
        client_name = client.get_configuration_setting(key="client").value
        client_version = client.get_configuration_setting(key="client_version").value
        facility_id = client.get_configuration_setting(key="facility_id").value

        # For users and classes, we'll assume they are stored as YAML/JSON strings in AppConfig
        users_setting = client.get_configuration_setting(key="users").value
        classes_setting = client.get_configuration_setting(key="classes").value
        
        users_raw = yaml.safe_load(users_setting)
        classes_raw = yaml.safe_load(classes_setting)

        users = []
        for u in users_raw:
            username = self._substitute_env(u.get("username"))
            password = self._substitute_env(u.get("password"))
            users.append(UserConfig(username=username, password=password))

        classes = [ClassConfig(**c) for c in classes_raw]

        return AppConfig(
            app_id=app_id,
            client=client_name,
            client_version=client_version,
            facility_id=facility_id,
            users=users,
            classes=classes
        )

    def _substitute_env(self, value: str) -> str:
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            result = os.getenv(env_var)
            if result is None:
                logging.warning(f"Environment variable '{env_var}' not found. Using the placeholder value: '{value}'")
                return value
            return result
        return value
