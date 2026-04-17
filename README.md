# Agente de Consultas SQL com Gemini

Este projeto implementa um agente de IA utilizando o modelo Gemini da Google para consultar um banco de dados SQLite de e-commerce. O agente responde perguntas em linguagem natural, gerando queries SQL automaticamente e retornando insights claros.

## Funcionalidades

- Consultas seguras ao banco de dados (apenas leitura)
- Integração com Gemini 2.5 Flash Lite
- Tratamento de erros e correção automática de queries
- Logging de queries para monitoramento
- Interface opcional com Streamlit

## Instalação

1. Clone o repositório:
   ```bash
   git clone <url-do-repositorio>
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure a chave da API do Gemini:
   - Edite o arquivo `.env` e adicione sua chave:
     ```
     GOOGLE_API_KEY=sua_chave_aqui
     ```

4. Certifique-se de que o arquivo `banco.db` esteja no diretório raiz (SQLite database fornecido).

## Como Usar

### Via Terminal
Execute o script principal:
```bash
python main.py
```
Digite sua pergunta sobre o banco de dados quando solicitado.

### Via Streamlit (Opcional)
```bash
streamlit run app.py
```

## Estrutura do Projeto

- `main.py`: Script principal com o agente e funções de consulta
- `requirements.txt`: Dependências do projeto
- `.env`: Arquivo de configuração para chave da API (não versionado)
- `banco.db`: Banco de dados SQLite
- `queries.log`: Log das queries executadas
- `app.py`: Interface Streamlit (opcional)

## Boas Práticas Implementadas

- Temperatura 0 para precisão em queries SQL
- Guardrails contra comandos de escrita
- Tratamento de erros com correção automática
- Saída estruturada com Pydantic
- Anonimização de dados (simulada)

## Tecnologias Utilizadas

- Python 3.x
- Google Generative AI
- SQLite3
- Pydantic
- Streamlit
