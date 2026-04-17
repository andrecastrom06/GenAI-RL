import streamlit as st
import pandas as pd
from main import agent_loop

# CONFIG
st.set_page_config(page_title="Agente SQL", layout="centered")

# CSS
st.markdown("""
    <style>
    /* Fundo geral */
    .stApp {
        background-color: #0d3b1e;
    }

    /* Título */
    h1 {
        color: #ffffff;
        text-align: center;
        font-weight: 700;
    }

    /* Label */
    label {
        color: #c8e6c9 !important;
        font-weight: 500;
    }

    /* Input */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        border: 2px solid #66bb6a;
        border-radius: 10px;
        padding: 10px;
        color: #1b5e20;
    }

    /* Botão */
    .stButton > button {
        background-color: #66bb6a;
        color: #0d3b1e;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }

    .stButton > button:hover {
        background-color: #81c784;
        color: #0d3b1e;
    }

    /* Caixa de resposta */
    .response-box {
        background-color: #ffffff;
        border: 2px solid #66bb6a;
        border-radius: 10px;
        padding: 15px;
        margin-top: 20px;
        color: #1b5e20;
        font-weight: 500;
    }

    /* Subtítulo */
    h3 {
        color: #a5d6a7;
    }
    </style>
""", unsafe_allow_html=True)

# UI
st.title("Agente de Consultas SQL com Gemini")

user_query = st.text_input("Digite sua pergunta sobre o banco de dados:")

if st.button("Consultar"):
    if user_query:
        with st.spinner("Consultando banco..."):
            answer = agent_loop(user_query)

        st.markdown("### Resultado:")

        if isinstance(answer, dict) and "data" in answer:
            df = pd.DataFrame(answer["data"], columns=answer["columns"])
            st.dataframe(df, width="stretch")

        else:
            st.markdown(f"<div class='response-box'>{answer}</div>", unsafe_allow_html=True)

    else:
        st.warning("Por favor, digite uma pergunta.")