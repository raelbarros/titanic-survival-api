# Titanic Survival API

API serverless para predição de sobrevivência de passageiros do Titanic, usando AWS Lambda + API Gateway + DynamoDB, provisionada com Terraform.

## Arquitetura

```
Cliente HTTP
    │
    ▼
API Gateway (OpenAPI 3.0)
    │
    ├── POST /sobreviventes ──► Lambda (Python) ──► model.pkl (S3)
    │                               │
    │                               ▼
    │                          DynamoDB (on-demand)
    │                               │
    ├── GET  /sobreviventes ─────────┤
    ├── GET  /sobreviventes/{id} ────┤
    └── DELETE /sobreviventes/{id} ──┘
```

## Pré-requisitos

| Ferramenta | Versão mínima |
|---|---|
| Terraform | >= 1.6 |
| AWS CLI | >= 2.0 (configurado com credenciais) |
| Docker | >= 20 (para build da Lambda Layer) |
| make | qualquer versão |

## Deploy

### 1. Clone o repositório e coloque o modelo

```bash
git clone <seu-repo>
cd titanic-api
cp /path/to/model.pkl modelo/model.pkl
```

### 2. Configure as credenciais AWS

```bash
aws configure
# ou exporte: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
```

### 3. Build e deploy completo

```bash
make deploy
```

Isso vai:
1. Compilar a Lambda Layer com numpy/pandas/scikit-learn via Docker
2. Executar `terraform init` + `terraform apply`
3. Fazer upload do `model.pkl` para S3
4. Criar Lambda, DynamoDB, API Gateway e IAM roles

### 4. Testar

```bash
make test
```

Ou manualmente:

```bash
API_URL=$(cd terraform && terraform output -raw api_url)

# Escorar um passageiro
curl -X POST "$API_URL/sobreviventes" \
  -H "Content-Type: application/json" \
  -d '{
    "passengers": [{
      "id": "rose-001",
      "pclass": 1,
      "sex": "female",
      "age": 17,
      "sibsp": 1,
      "parch": 2,
      "fare": 151.55,
      "embarked": "S"
    }]
  }'

# Listar todos os passageiros avaliados
curl "$API_URL/sobreviventes"

# Listar com paginação
curl "$API_URL/sobreviventes?limit=5&last_key=rose-001"

# Consultar passageiro específico
curl "$API_URL/sobreviventes/rose-001"

# Deletar passageiro
curl -X DELETE "$API_URL/sobreviventes/rose-001"
```

## Endpoints

| Método | Path | Descrição |
|---|---|---|
| `POST` | `/sobreviventes` | Escorar um ou mais passageiros |
| `GET` | `/sobreviventes` | Listar todos os passageiros avaliados |
| `GET` | `/sobreviventes/{id}` | Consultar passageiro por ID |
| `DELETE` | `/sobreviventes/{id}` | Remover passageiro |

### Exemplo de request (POST)

```json
{
  "passengers": [
    {
      "id": "p-001",
      "pclass": 3,
      "sex": "male",
      "age": 22,
      "sibsp": 1,
      "parch": 0,
      "fare": 7.25,
      "embarked": "S"
    }
  ]
}
```

### Exemplo de response (POST)

```json
{
  "results": [
    {
      "id": "p-001",
      "survival_probability": 0.1243,
      "survived": false
    }
  ]
}
```

## Estrutura do repositório

```
├── lambda/
│   ├── handler.py          # Código da Lambda (todos os endpoints)
│   └── requirements.txt    # Dependências Python
├── terraform/
│   ├── main.tf             # Provider e backend
│   ├── variables.tf        # Variáveis configuráveis
│   ├── s3.tf               # Bucket para o model.pkl
│   ├── dynamodb.tf         # Tabela on-demand
│   ├── lambda.tf           # Função + Layer + CloudWatch
│   ├── api_gateway.tf      # API Gateway com contrato OpenAPI
│   ├── iam.tf              # Roles e policies
│   └── outputs.tf          # URL da API e nomes dos recursos
├── openapi/
│   └── openapi.yaml        # Contrato OpenAPI 3.0
├── modelo/
│   └── model.pkl           # Modelo treinado (não versionado no git)
├── Makefile                # Comandos de build, deploy e test
└── README.md
```

## Decisões de design

**Por que Lambda e não ECS/Fargate?**
O volume de requisições é baixo e esporádico. Lambda é serverless, escala a zero e tem custo zero quando não há tráfego — ideal para este case.

**Por que o model.pkl fica no S3?**
Lambda tem limite de 50MB comprimido no pacote de deploy. numpy + pandas + scikit-learn já consomem boa parte desse espaço. Armazenar o modelo no S3 permite atualizar o modelo sem re-deploy da função. O modelo é carregado em memória no cold start e cacheado na execução subsequente (warm).

**Por que DynamoDB on-demand?**
O case explicitamente pede para não provisionar capacidade. `PAY_PER_REQUEST` cobra apenas por operação, sem custo fixo de throughput.

**Por que uma única Lambda para todos os endpoints?**
Simplifica o deploy e o Terraform. Para escala maior, cada método poderia ter sua própria Lambda — mas para este case a função única com roteamento interno é suficiente.

## Destruir a infraestrutura

```bash
make destroy
```
