import sqlite3
import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import errors as genai_errors
from pydantic import BaseModel
import logging
import re

estados = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins"
}

# Carregar variáveis de ambiente
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Configurações
DATABASE_PATH = "banco.db"
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
SCHEMA_CACHE = None
DISTINCT_VALUES_CACHE = {}

def get_connection():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)

# Logging
logging.basicConfig(filename='queries.log', level=logging.INFO, format='%(asctime)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)

# Segurança de query
ALLOWED_STATEMENTS = ("SELECT", "WITH")

def is_safe_query(query: str) -> bool:
    query_clean = re.sub(r'--.*?(\n|$)', '', query)
    query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
    query_clean = query_clean.strip().upper()

    if ";" in query_clean[:-1]:
        return False

    return query_clean.startswith(ALLOWED_STATEMENTS)

def executar_query(query: str) -> dict:
    logging.info(f"Executando query SQL: {query}")

    if not is_safe_query(query):
        logging.warning("Query bloqueada por política de segurança.")
        return {"error": "Query não permitida. Apenas SELECT é autorizado."}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            return {"columns": columns, "data": results}

    except Exception as e:
        return {"error": str(e)}

# Schema e cache
def get_schema() -> dict:
    global SCHEMA_CACHE
    if SCHEMA_CACHE is not None:
        return SCHEMA_CACHE

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

def get_distinct_values(table: str, column: str) -> dict:
    cache_key = f"{table}.{column}"

    if cache_key in DISTINCT_VALUES_CACHE:
        return DISTINCT_VALUES_CACHE[cache_key]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT {column} FROM {table} LIMIT 100;")
        rows = cursor.fetchall()

    result = {"table": table, "column": column, "values": [row[0] for row in rows]}
    DISTINCT_VALUES_CACHE[cache_key] = result
    return result

# Pydantic Models para resposta
class QueryResult(BaseModel):
    columns: list[str]
    data: list[list]

class QueryResponse(BaseModel):
    query: str
    results: QueryResult | None
    explanation: str

# Prompt
system_prompt = """
Você é um analista de dados especialista em E-commerce.
Responda sempre em português.
Use executar_query(query) para consultar dados.
Nunca execute comandos de escrita.
Responda de forma direta com o resultado final.
"""

# Configuração do Gemini
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
    tools=[EXECUTAR_QUERY_TOOL, GET_SCHEMA_TOOL, GET_DISTINCT_VALUES_TOOL],
    automatic_function_calling=genai.types.AutomaticFunctionCallingConfig(
        disable=False,
        maximum_remote_calls=3
    ),
    system_instruction=system_prompt
)

# Funções auxiliares
def format_query_result(result: dict) -> str:
    if "error" in result:
        return f"Erro: {result['error']}"

    columns = result.get("columns", [])
    rows = result.get("data", [])

    if not rows:
        return "Nenhum resultado encontrado."

    header = " | ".join(columns)
    body = "\n".join(" | ".join(map(str, row)) for row in rows[:10])

    return f"{header}\n{body}"

def format_schema(schema: dict) -> str:
    return "\n".join(
        f"{table}: {', '.join(col['name'] for col in cols)}"
        for table, cols in schema.items()
    )

def normalizar_estados(texto: str) -> str:
    for sigla, nome in estados.items():
        # substitui nome completo pela sigla
        texto = re.sub(rf"\b{nome}\b", sigla, texto, flags=re.IGNORECASE)
    return texto

# Loop de execução do agente
def agent_loop(user_query: str) -> dict:
    user_query = normalizar_estados(user_query)
    schema_text = format_schema(get_schema())
    chat = genai_client.chats.create(model=MODEL_NAME, config=CHAT_CONFIG)

    try:
        response = chat.send_message(
            f"{system_prompt}\n\nSchema:\n{schema_text}\n\nPergunta: {user_query}"
        )
    except Exception as e:
        return {"error": str(e)}

    last_result = None
    final_answer = None

    for _ in range(3):
        if not response.candidates:
            break

        candidate = response.candidates[0] if response.candidates else None
        
        if not candidate:
            logging.warning("Sem candidates na resposta")
            break

        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None

        if not parts:
            logging.warning("Resposta sem parts")
            break

        for part in parts:
            if getattr(part, 'function_call', None):
                fn = part.function_call.name
                args = part.function_call.args

                if fn == "executar_query":
                    last_result = executar_query(args["query"])
                elif fn == "get_schema":
                    last_result = get_schema()
                elif fn == "get_distinct_values":
                    last_result = get_distinct_values(args["table"], args["column"])

                response = chat.send_message(
                    genai.types.Part.from_function_response(
                        name=fn,
                        response=last_result
                    )
                )
                break
            else:
                final_answer = getattr(part, 'text', '').strip()

        if final_answer:
            break

    # Resposta final estruturada
    result_obj = None

    if last_result and "columns" in last_result:
        result_obj = QueryResult(**last_result)

    explanation = final_answer or (
        format_query_result(last_result) if last_result else "Sem resposta."
    )

    return QueryResponse(
        query=user_query,
        results=result_obj,
        explanation=explanation
    ).dict()

if __name__ == "__main__":
    user_input = input("Pergunta: ")
    response = agent_loop(user_input)

    print("\n=== RESPOSTA ===")
    print(response["explanation"])

    if response["results"]:
        print("\n=== DADOS ===")
        print(response["results"])