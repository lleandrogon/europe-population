import azure.functions as func
import pandas as pd
import os
import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="bronze")
def bronze(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Iniciando execução da função bronze!")

    KEY_VAULT_URL = os.environ.get("KEY_VAULT_URL", "https://eupopkeys.vault.azure.net/")

    credential = DefaultAzureCredential()
    vault_client = SecretClient(vault_url = KEY_VAULT_URL, credential = credential)

    account_name = vault_client.get_secret("storage-account-name").value
    account_key = vault_client.get_secret("storage-account-key").value

    storage_options = {
        "account_name": account_name,
        "account_key": account_key
    }

    try:
        df = pd.read_csv(
            "abfs://raw/europe.csv",
            storage_options = storage_options
        )

        logging.info("✅ Dados brutos lidos com sucesso!")
    except Exception as e:
        logging.error(f"❌ Erro ao ler os dados brutos: {e}")

        return func.HttpResponse(
            "❌ Erro ao ler os dados brutos!",
            status_code = 500
        )

    try:
        df.to_parquet(
            "abfs://bronze/europopulation.parquet",
            index = False,
            storage_options = storage_options
        )

        logging.info("✅ Dados salvos na bronze com sucesso!")

        return func.HttpResponse(
            "✅ Azure Function executada com sucesso!",
            status_code = 200
        )
    except Exception as e:
        logging.error(f"❌ Erro ao salvar dados na bronze: {e}")

        return func.HttpResponse(
            "❌ Azure Function falhou!",
            status_code = 500
        )