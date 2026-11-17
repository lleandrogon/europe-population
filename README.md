# Pipeline ETL de População da Europa

Projeto de Azure Functions em Python que organiza dados de população dos países europeus em um lakehouse com as camadas **bronze**, **silver** e **gold**.

As funções HTTP são acionadas separadamente e armazenam os dados em um Azure Data Lake Storage Gen2 usando Apache Parquet. O acesso às credenciais do Storage Account é feito por meio do Azure Key Vault.

## Arquitetura

```text
Azure Data Lake Gen2
raw/europe.csv
       |
       v
HTTP Function /api/bronze
       |
       v
bronze/europopulation.parquet
       |
       v
HTTP Function /api/silver
       |
       v
silver/europopulation.parquet
       |
       v
HTTP Function /api/gold
       |
       v
gold/europopulation_rank.parquet
```

As três etapas são independentes. É necessário executar a bronze antes da silver e a silver antes da gold.

## Processamento

### Bronze

Rota: `GET/POST /api/bronze`

- Lê `europe.csv` da camada `raw`.
- Converte o DataFrame para Parquet.
- Grava o resultado em `bronze/europopulation.parquet`.

### Silver

Rota: `GET/POST /api/silver`

- Lê os dados da camada `bronze`.
- Renomeia `Unnamed: 0` para `id`.
- Renomeia `Continent` para `continent`.
- Renomeia `population_per_sq_km` para `population_density`.
- Remove a coluna `continent`.
- Converte `area` e `population` para inteiro.
- Converte `population_density` para número decimal.
- Grava o resultado em `silver/europopulation.parquet`.

### Gold

Rota: `GET/POST /api/gold`

- Lê os dados da camada `silver`.
- Calcula o ranking de população por meio de `DENSE_RANK`.
- Ordena os registros pela população em ordem decrescente.
- Grava o resultado em `gold/europopulation_rank.parquet`.

## Estrutura do projeto

```text
.
|-- function_app.py       # Definicao das Azure Functions e transformacoes
|-- host.json             # Configuracoes do Azure Functions Host
|-- local.settings.json   # Configuracoes locais; nao versionar valores sensiveis
|-- requirements.txt      # Dependencias Python
|-- .gitignore
`-- .vscode/
    |-- extensions.json
    |-- launch.json
    |-- settings.json
    `-- tasks.json
```

## Tecnologias

- Python
- Azure Functions
- Azure Data Lake Storage Gen2
- Azure Key Vault
- Azure Identity com `DefaultAzureCredential`
- Pandas
- DuckDB
- PyArrow
- adlfs

## Pré-requisitos

- Python 3.10 ou superior
- Azure Functions Core Tools
- Azure CLI
- Extensões do Azure Functions e Python no VS Code
- Uma assinatura Azure com:
  - Azure Storage Account habilitado para HNS (Data Lake Gen2)
  - Azure Key Vault
  - Permissão para ler secrets do Key Vault
  - Permissão de leitura e escrita no Storage Account

## Recursos Azure necessários

O Storage Account deve conter os containers ou diretórios:

```text
raw
bronze
silver
gold
```

O arquivo de origem deve estar disponível em:

```text
raw/europe.csv
```

O Azure Key Vault deve conter os secrets:

| Secret | Conteúdo |
|---|---|
| `storage-account-name` | Nome do Azure Storage Account |
| `storage-account-key` | Chave de acesso do Azure Storage Account |

O código usa `DefaultAzureCredential`. Em ambiente local, autentique-se com o Azure CLI:

```powershell
az login
```

Para executar pela Azure Function, atribua uma identidade gerenciada à Function App e conceda a ela acesso ao Key Vault e ao Storage Account.

## Configuração local

Crie o ambiente virtual e instale as dependências:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Configure o valor do Key Vault em `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "KEY_VAULT_URL": "https://SEU-KEY-VAULT.vault.azure.net/"
  }
}
```

Se não estiver usando o Azurite, substitua `UseDevelopmentStorage=true` pela string de conexão ou configuração de armazenamento usada pela sua Azure Function.

Na configuração atual, `KEY_VAULT_URL` possui um valor padrão no código. Para ambientes que devem ser completamente configuráveis, considere remover o valor padrão e exigir a variável no ambiente.

## Executando localmente

Pelo Azure Functions Core Tools:

```powershell
func start
```

Pelo VS Code, execute a tarefa `func: host start` ou use a configuração de depuração `Attach to Python Functions`.

As URLs padrão serão semelhantes a:

```text
http://localhost:7071/api/bronze
http://localhost:7071/api/silver
http://localhost:7071/api/gold
```

## Executando no Azure

Depois de publicar a Function App, configure as seguintes variáveis de ambiente:

| Variável | Descrição |
|---|---|
| `KEY_VAULT_URL` | URL do Azure Key Vault |
| `FUNCTIONS_WORKER_RUNTIME` | Deve ser `python` |

Crie ou confirme a configuração de `AzureWebJobsStorage` exigida pelo Azure Functions.

As rotas exigem uma chave de função, porque são configuradas com `AuthLevel.FUNCTION`. Para chamar uma função publicada:

```text
https://SUA-FUNCTION.azurewebsites.net/api/bronze?code=SUA_FUNCTION_KEY
```

Substitua `bronze` pelo nome da etapa desejada.

## Permissões mínimas sugeridas

### Azure Key Vault

A identidade usada pela aplicação precisa da função ou política equivalente a:

- Ler secrets

No modelo RBAC, a role indicada é `Key Vault Secrets User`.

### Azure Storage

A identidade usada pela aplicação precisa de acesso aos blobs e dados:

- `Storage Blob Data Contributor`

## Segurança

- Não versione keys, SAS tokens, connection strings ou arquivos `local.settings.json` preenchidos.
- Use `DefaultAzureCredential` em vez de credenciais embutidas no código.
- Prefira Managed Identity em produção.
- Conceda apenas os permissões necessárias em Key Vault e Storage.
- Mantenha os secrets fora dos logs e das respostas HTTP.

O projeto já inclui `local.settings.json` no `.gitignore`.

## Saída esperada

Em caso de sucesso, cada endpoint retorna HTTP `200` com uma mensagem informando que a execução foi concluída.

Em caso de falha:

- A bronze retorna HTTP `500` ao não conseguir ler ou salvar dados.
- A silver retorna HTTP `500` ao não conseguir ler ou salvar dados.
- A gold retorna HTTP `500` ao não conseguir ler ou salvar dados.
