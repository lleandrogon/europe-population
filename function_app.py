import azure.functions as func
import pandas as pd
import duckdb
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

@app.route(route="silver")
def silver(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Iniciando execução da função silver!")

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
        df = pd.read_parquet(
            "abfs://bronze/europopulation.parquet",
            storage_options = storage_options
        )

        logging.info("✅ Dados da bronze lidos com sucesso!")
    except Exception as e:
        logging.error(f"❌ Erro ao ler os dados da bronze: {e}")

        return func.HttpResponse(
            "❌ Erro ao ler os dados da bronze!",
            status_code = 500
        )

    df = df.rename(columns = {
        "Unnamed: 0": "id",
        "Continent": "continent",
        "population_per_sq_km": "population_density"
    })

    df = df.drop(columns = ["continent"])

    df["area"] = (
        df["area"] \
            .str.replace(" km²", "", regex = False) \
            .str.replace(",", "", regex = False) \
            .astype(int)
    )

    df["population"] = (
        df["population"] \
            .str.replace(",", "", regex = False) \
            .astype(int)
    )

    df["population_density"] = (
        df["population_density"] \
            .str.replace(",", ".", regex = False) \
            .astype(float)
    )

    try:
        df.to_parquet(
            "abfs://silver/europopulation.parquet",
            index = False,
            storage_options = storage_options
        )

        logging.info("✅ Dados salvos na silver com sucesso!")

        return func.HttpResponse(
            "✅ Azure Function executada com sucesso!",
            status_code = 200
        )
    except Exception as e:
        logging.error(f"❌ Erro ao salvar dados na silver: {e}")

        return func.HttpResponse(
            "❌ Azure Function falhou!",
            status_code = 500
        )

@app.route(route="gold")
def gold(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Iniciando execução da função gold!")

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
        df = pd.read_parquet(
            "abfs://silver/europopulation.parquet",
            storage_options = storage_options
        )

        logging.info("✅ Dados da silver lidos com sucesso!")
    except Exception as e:
        logging.error(f"❌ Erro ao ler os dados da silver: {e}")

        return func.HttpResponse(
            "❌ Erro ao ler os dados da silver!",
            status_code = 500
        )

    df = duckdb.sql("""--sql
        SELECT 
            *,
            DENSE_RANK() OVER(ORDER BY population DESC) AS population_rank
        FROM df
        ORDER BY population DESC;
    """).df()

    try:
        df.to_parquet(
            "abfs://gold/europopulation_rank.parquet",
            index = False,
            storage_options = storage_options
        )

        logging.info("✅ Dados salvos na gold com sucesso!")

        return func.HttpResponse(
            "✅ Azure Function executada com sucesso!",
            status_code = 200
        )
    except Exception as e:
        logging.error(f"❌ Erro ao salvar dados na gold: {e}")

        return func.HttpResponse(
            "❌ Azure Function falhou!",
            status_code = 500
        )