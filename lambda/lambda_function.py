import json
import os
import boto3
import pickle
import secrets
import pandas as pd
from typing import Any, Dict
from loguru import logger
from decimal import Decimal


# Clients AWS
s3_client = boto3.client("s3")
dydb_client = boto3.resource("dynamodb")


# Variáveis globais
_TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "dynamo_titanic-api")
_MODEL_BUCKET = os.environ.get("MODEL_BUCKET", "s3-titanic-api")
_MODEL_KEY = os.environ.get("MODEL_KEY", "model.pkl")

_MODEL = None


def load_model():
    """
    Carrega o modelo do S3 e mantém na memória.
    """
    global _MODEL

    if _MODEL is None:
        logger.info("Carregando modelo do S3")
        
        resp = s3_client.get_object(Bucket=_MODEL_BUCKET, Key=_MODEL_KEY)
        _MODEL = pickle.load(resp["Body"])

        logger.success("Modelo carregado com sucesso")
    else:
        logger.debug("Modelo já carregado")

    return _MODEL


def post_predict_model_and_save_db(envelop):
    """
    Recebe lista de passageiros, executa inferência, salva resultados no DynamoDB
    e retorna o resultado da predição.
    """
    try:
        body = json.loads(envelop.get("body") or "{}")

        if not body:
            logger.warning("Requisição POST recebida com body vazio")
            return _response(400, {"message": "Body vazio"})

        passengers = body.get("passengers")
        if not passengers or not isinstance(passengers, list):
            logger.warning("Campo 'passengers' ausente, vazio ou inválido")
            return _response(400, {"message": "Lista de passageiros vazia ou inválida"})

        logger.info(f"Iniciando processamento de predição | total_passengers={len(passengers)}")

        model = load_model()
        table = dydb_client.Table(_TABLE_NAME)

        results = []

        for p in passengers:
            p_id = p.get("id") or str(secrets.randbelow(100))

            logger.info(f"Processando passageiro id='{p_id}'")

            X = _pre_process(p)

            # Garante a ordem correta das features
            X = X[model.feature_names_in_]
            
            # Realiza o predict
            survived, predict_proba = _exec_predict(model, X)
            logger.info("Inferência concluída")

            # Transforma dict para salvar no db
            item_to_save = X.to_dict(orient="records")[0]
            item_to_save["predict_proba"] = predict_proba
            item_to_save["survived"] = survived
            item_to_save["id"] = p_id

            _save_db(table, item_to_save)

            results.append(
                {
                    "id": p_id,
                    "survived": survived,
                    "predict_proba": predict_proba,
                }
            )

        logger.success("Processamento finalizado com sucesso | total salvos={len(results)}")
        return _response(200, {"result": results})

    except Exception as e:
        logger.exception("Erro ao processar requisição POST de predição")
        return _response(500, {"message": str(e)})


def get_all_saved_data():
    """
    Busca todos os registros da tabela.
    """
    try:
        logger.info("Buscando registros no DynamoDB")

        table = dydb_client.Table(_TABLE_NAME)

        results = []
        response = table.scan()
        results.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            results.extend(response.get("Items", []))

        results_normalized = [_normalize_item(i) for i in results]

        logger.success(f"Consulta concluída | total_registros={len(results_normalized)}")
        return _response(200, {"result": results_normalized})

    except Exception as e:
        logger.exception("Erro ao buscar todos os registros")
        return _response(500, {"message": str(e)})


def get_saved_data_by_id(p_id: str):
    """
    Busca um registro pelo ID.
    """
    try:
        logger.info(f"Buscando registro por ID | id={p_id}")

        table = dydb_client.Table(_TABLE_NAME)
        result = table.get_item(Key={"id": p_id})
        item = result.get("Item")

        if not item:
            logger.warning(f"Registro não encontrado | id={p_id}")
            return _response(404, {"message": f"Registro '{p_id}' não encontrado"})

        logger.success(f"Registro encontrado | id={p_id}")
        return _response(200, _normalize_item(item))

    except Exception as e:
        logger.exception(f"Erro ao buscar registro por ID | id={p_id}")
        return _response(500, {"message": str(e)})


def delete_data_by_id(p_id: str):
    """
    Remove um registro pelo ID.
    """
    try:
        logger.info(f"Solicitação de exclusão recebida | id={p_id}")

        table = dydb_client.Table(_TABLE_NAME)
        result = table.get_item(Key={"id": p_id})

        if not result.get("Item"):
            logger.warning(f"Tentativa de exclusão de registro inexistente | id={p_id}")
            return _response(404, {"message": f"Registro '{p_id}' não encontrado"})

        table.delete_item(Key={"id": p_id})

        logger.success(f"Registro deletado com sucesso | id={p_id}")
        return _response(200, {"message": f"Passageiro '{p_id}' deletado"})

    except Exception as e:
        logger.exception(f"Erro ao deletar registro | id='{p_id}'")
        return _response(500, {"message": str(e)})


def lambda_handler(event, context):
    """
    Função principal da AWS Lambda.
    Faz o roteamento baseado em método HTTP e path.
    """
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}

    logger.info(f"Nova requisição recebida | method='{http_method}' path='{path}' path_params={path_params}")

    if http_method == "POST" and path == "/sobreviventes":
        return post_predict_model_and_save_db(event)

    if http_method == "GET" and path == "/sobreviventes":
        return get_all_saved_data()

    if http_method == "GET" and "id" in path_params:
        return get_saved_data_by_id(path_params["id"])

    if http_method == "DELETE" and "id" in path_params:
        return delete_data_by_id(path_params["id"])

    logger.warning(f"Rota não encontrada | method='{http_method}' path='{path}' path_params={path_params}")
    return _response(404, {"message": "Rota não encontrada"})


def _to_number(value):
    """
    Converte Decimal para int ou float.
    """
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


def _normalize_item(item: dict) -> dict:
    """
    Converte dados do DynamoDB para tipos Python nativos.
    """
    return {
        "id": item.get("id"),
        "Age": _to_number(item.get("Age")),
        "Embarked_Q": _to_number(item.get("Embarked_Q")),
        "Embarked_S": _to_number(item.get("Embarked_S")),
        "Fare": _to_number(item.get("Fare")),
        "Parch": _to_number(item.get("Parch")),
        "Pclass": _to_number(item.get("Pclass")),
        "predict_proba": _to_number(item.get("predict_proba")),
        "Sex_male": _to_number(item.get("Sex_male")),
        "SibSp": _to_number(item.get("SibSp")),
        "survived": _to_number(item.get("survived")),
    }


def _response(status_code: int, body: dict) -> dict:
    """
    Padroniza o retorno HTTP da Lambda.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def _pre_process(data: dict) -> pd.DataFrame:
    """
    Converte payload em DataFrame e aplica o processamento do modelo.
    """
    logger.info("Iniciando processamento dos dados")

    df = pd.DataFrame([data])

    df = df.rename(
        columns={
            "pclass": "Pclass",
            "parch": "Parch",
            "fare": "Fare",
            "age": "Age",
            "sibsp": "SibSp",
        }
    )
    # one-hot encoder
    df["Sex_male"] = (df["sex"] == "male").astype(int)
    df["Embarked_Q"] = (df["embarked"] == "Q").astype(int)
    df["Embarked_S"] = (df["embarked"] == "S").astype(int)

    df = df.drop(columns=["sex", "embarked"])

    logger.debug("Processamento concluído")
    return df


def _exec_predict(model, X: pd.DataFrame):
    """
    Executa a inferência do modelo.
    """
    logger.debug("Executando inferência")

    proba = float(model.predict_proba(X)[0][1])
    survived = int(proba >= 0.5)

    logger.debug(f"Resultado da inferência | survived={survived} predict_proba={proba:.6f}")

    return survived, proba


def _save_db(table, payload):
    """
    Salva item no DynamoDB convertendo floats para Decimal.
    """
    item = {}

    for key, value in payload.items():
        if isinstance(value, float):
            item[key] = Decimal(str(value))
        else:
            item[key] = value

    logger.info("Salvando item no DynamoDB")

    table.put_item(Item=item)
    logger.success(f"Item salvo com sucesso | id={item.get("id")}")