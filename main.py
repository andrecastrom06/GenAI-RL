import sqlite3
import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import errors as genai_errors
from pydantic import BaseModel
import logging

# Carregar variáveis de ambiente
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Conectar ao banco
DATABASE_PATH = "banco.db"
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
SCHEMA_CACHE = None
DISTINCT_VALUES_CACHE = {}

def get_connection():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)

# Configurar logging
logging.basicConfig(filename='queries.log', level=logging.INFO, format='%(asctime)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)

# Função para executar query
def executar_query(query: str) -> dict:
    logging.info(f"Executando query SQL: {query}")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            result_dict = {"columns": columns, "data": results}
            return anonimizar_dados(result_dict)
    except Exception as e:
        return {"error": str(e)}

# Função para anonimizar dados (simulada)
def anonimizar_dados(results):
    # Simulação: substituir apenas campos sensíveis por placeholders.
    sensitive_fields = {"nome_cliente", "email", "cpf", "telefone", "endereco", "bairro", "cidade", "estado"}
    if "data" in results:
        anonymized_data = []
        for row in results["data"]:
            row_list = list(row)
            for i, col in enumerate(results["columns"]):
                column_name = col.lower()
                if column_name in sensitive_fields:
                    row_list[i] = "ANONIMIZADO"
            anonymized_data.append(tuple(row_list))
        results["data"] = anonymized_data
    return results

# Função para obter schema
def get_schema() -> dict:
    global SCHEMA_CACHE
    if SCHEMA_CACHE is not None:
        logging.info("Usando schema em cache")
        return SCHEMA_CACHE

    logging.info("Consultando schema do banco de dados")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            schema[table_name] = [{"name": col[1], "type": col[2]} for col in columns]
    SCHEMA_CACHE = schema
    return schema

# Função para obter valores distintos de uma coluna
def get_distinct_values(table: str, column: str) -> dict:
    cache_key = f"{table}.{column}"
    if cache_key in DISTINCT_VALUES_CACHE:
        logging.info(f"Usando distinct values em cache para {cache_key}")
        return DISTINCT_VALUES_CACHE[cache_key]

    logging.info(f"Consultando valores distintos de {table}.{column}")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT {column} FROM {table} LIMIT 100;")
        rows = cursor.fetchall()
    result = {"table": table, "column": column, "values": [row[0] for row in rows]}
    DISTINCT_VALUES_CACHE[cache_key] = result
    return result

# System Prompt
system_prompt = """
Você é um analista de dados especialista em E-commerce.
Seu objetivo é ajudar usuários não técnicos a extrair insights do banco de dados SQL.
Use as ferramentas disponíveis para consultar dados e responda somente com a resposta final em português.
Se precisar saber quais valores uma coluna pode ter, use a função get_distinct_values(table, column).
Use a função executar_query(query) para consultar dados e não retorne o SQL da consulta como resposta final.
Não explique a análise ou o processo interno.
Não execute comandos de escrita (INSERT, UPDATE, DELETE, DROP). Apenas consultas de leitura.
"""

# Configurar Gemini
genai_client = genai.Client(api_key=API_KEY)
EXECUTAR_QUERY_TOOL = genai.types.Tool(
    function_declarations=[
        genai.types.FunctionDeclaration.from_callable_with_api_option(
            callable=executar_query,
            api_option="GEMINI_API"
        )
    ]
)
GET_SCHEMA_TOOL = genai.types.Tool(
    function_declarations=[
        genai.types.FunctionDeclaration.from_callable_with_api_option(
            callable=get_schema,
            api_option="GEMINI_API"
        )
    ]
)
GET_DISTINCT_VALUES_TOOL = genai.types.Tool(
    function_declarations=[
        genai.types.FunctionDeclaration.from_callable_with_api_option(
            callable=get_distinct_values,
            api_option="GEMINI_API"
        )
    ]
)
CHAT_CONFIG = genai.types.GenerateContentConfig(
    temperature=0,
    max_output_tokens=256,
    tools=[EXECUTAR_QUERY_TOOL, GET_SCHEMA_TOOL, GET_DISTINCT_VALUES_TOOL],
    automatic_function_calling=genai.types.AutomaticFunctionCallingConfig(disable=False, maximum_remote_calls=3),
    system_instruction=system_prompt
)

# Modelo de resposta estruturada
class QueryResponse(BaseModel):
    query: str
    results: dict
    explanation: str

# Helper para formatar resultados de query
def format_query_result(result):
    if not isinstance(result, dict):
        return str(result)
    if "error" in result:
        return f"Erro na consulta: {result['error']}"

    columns = result.get("columns", [])
    rows = result.get("data", [])
    if not rows:
        return "Nenhum registro encontrado."

    if len(columns) == 1:
        lines = [f"{idx + 1}. {row[0]}" for idx, row in enumerate(rows[:20])]
        if len(rows) > 20:
            lines.append(f"... e mais {len(rows) - 20} itens ...")
        return f"{columns[0]}:\n" + "\n".join(lines)

    header = " | ".join(columns)
    body_lines = [" | ".join(str(value) for value in row) for row in rows[:10]]
    if len(rows) > 10:
        body_lines.append(f"... e mais {len(rows) - 10} linhas ...")
    return header + "\n" + "\n".join(body_lines)

# Helper para normalizar respostas em texto
def normalize_answer_text(answer):
    if not isinstance(answer, str):
        return answer
    if "\n" in answer:
        return answer

    # Organiza listas de itens separados por vírgula
    if ", " in answer:
        pieces = [piece.strip() for piece in answer.split(",") if piece.strip()]
        if len(pieces) > 1:
            # Se for lista de pares chave:valor ou itens curtos, troque por nova linha
            if all(":" in piece or len(piece.split()) <= 5 for piece in pieces):
                return "\n".join(pieces)

    # Organiza itens separados por ponto-e-vírgula
    if "; " in answer:
        pieces = [piece.strip() for piece in answer.split(";") if piece.strip()]
        if len(pieces) > 1:
            return "\n".join(pieces)

    return answer

# Helper para formatar schema
def format_schema(schema):
    lines = []
    for table, columns in schema.items():
        col_text = ", ".join(f"{col['name']} ({col['type']})" for col in columns)
        lines.append(f"{table}: {col_text}")
    return "\n".join(lines)

# Loop de raciocínio
def agent_loop(user_query):
    logging.info(f"Iniciando agent_loop para pergunta: {user_query}")
    schema_text = format_schema(get_schema())
    chat = genai_client.chats.create(model=MODEL_NAME, config=CHAT_CONFIG)
    try:
        response = chat.send_message(
            f"{system_prompt}\n\nTabelas disponíveis:\n{schema_text}\n\nPergunta do usuário: {user_query}"
        )
    except genai_errors.ClientError as e:
        logging.error(f"Erro da API Gemini: {e}")
        return (
            "Quota da API excedida ou erro de chave. Por favor, aguarde alguns segundos ou verifique seu plano/billing "
            "e tente novamente." 
        )
    except Exception as e:
        logging.error(f"Erro ao enviar mensagem ao Gemini: {e}")
        return "Erro de comunicação com o serviço de IA. Tente novamente mais tarde."

    last_result = None
    final_answer = None
    attempt = 0
    MAX_AGENT_ATTEMPTS = 3

    # Processar a resposta e extrair tool calls
    while response.candidates and attempt < MAX_AGENT_ATTEMPTS:
        attempt += 1
        logging.info(f"[attempt {attempt}] Processando response com {len(response.candidates)} candidates")
        no_tool_call = True

        first_candidate = response.candidates[0]
        content = getattr(first_candidate, 'content', None)
        parts = getattr(content, 'parts', None) if content is not None else None

        if not parts:
            logging.warning("Resposta do modelo não contém partes de conteúdo para processar.")
            break

        for part in parts:
            part_text = getattr(part, 'text', None)
            part_text_str = part_text.strip() if isinstance(part_text, str) else ''
            logging.info(f"Parte recebida: function_call={hasattr(part, 'function_call') and part.function_call is not None}; text='{part_text_str}'")
            if getattr(part, 'function_call', None):
                no_tool_call = False
                function_name = part.function_call.name
                args = part.function_call.args
                logging.info(f"Detectada função chamada: {function_name}")

                if function_name == "executar_query":
                    last_result = executar_query(args["query"])
                    logging.info(f"Query executada: {args['query']}")
                elif function_name == "get_schema":
                    last_result = get_schema()
                    logging.info("Resultado de get_schema retornado")
                elif function_name == "get_distinct_values":
                    last_result = get_distinct_values(args["table"], args["column"])
                    logging.info(f"Valores distintos retornados para {args['table']}.{args['column']}")

                try:
                    response = chat.send_message(
                        genai.types.Part.from_function_response(
                            name=function_name,
                            response=last_result
                        )
                    )
                except genai_errors.ClientError as e:
                    logging.error(f"Erro da API Gemini durante a troca de função: {e}")
                    return (
                        "Quota da API excedida ou erro de chave. Por favor, aguarde alguns segundos ou verifique seu plano/billing "
                        "e tente novamente."
                    )
                except Exception as e:
                    logging.error(f"Erro ao enviar resposta de função ao Gemini: {e}")
                    return "Erro de comunicação com o serviço de IA. Tente novamente mais tarde."
                break
            else:
                part_text = getattr(part, 'text', None)
                final_answer = part_text.strip() if isinstance(part_text, str) else ''
                logging.info(f"Resposta final recebida do modelo: {final_answer}")

        if final_answer:
            final_answer = normalize_answer_text(final_answer)
            logging.info(f"Finalizando agent_loop com resposta final: {final_answer}")
            return final_answer

        if no_tool_call:
            logging.warning("Nenhuma função chamada encontrada e sem resposta final. Saindo do loop para evitar repetição.")
            break

        if not response.candidates:
            break

    if last_result is not None:
        logging.info("Finalizando agent_loop com resultado de query formatado")
        return format_query_result(last_result)

    logging.warning("agent_loop não conseguiu gerar resposta")
    return "Não foi possível gerar uma resposta. Tente novamente com outra pergunta."

# Exemplo de uso
if __name__ == "__main__":
    user_input = input("Digite sua pergunta sobre o banco de dados: ")
    answer = agent_loop(user_input)
    print(answer)