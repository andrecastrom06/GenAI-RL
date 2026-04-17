import streamlit as st
import pandas as pd
from main import agent_loop

# CONFIG
st.set_page_config(page_title="Agente SQL", layout="centered")

# CSS (mantido igual)
st.markdown("""
    <style>
    .stApp { background-color: #0d3b1e; }
    h1 { color: #ffffff; text-align: center; font-weight: 700; }
    label { color: #c8e6c9 !important; font-weight: 500; }
    .stTextInput > div > div > input {
        background-color: #ffffff;
        border: 2px solid #66bb6a;
        border-radius: 10px;
        padding: 10px;
        color: #1b5e20;
    }
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
    }
    .response-box {
        background-color: #ffffff;
        border: 2px solid #66bb6a;
        border-radius: 10px;
        padding: 15px;
        margin-top: 20px;
        color: #1b5e20;
    }
    h3 { color: #a5d6a7; }
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

        # 🔥 NOVO FORMATO
        if isinstance(answer, dict):

            # Mostrar explicação sempre
            explanation = answer.get("explanation", "")
            
            # Mostrar tabela se existir
            results = answer.get("results")

            if explanation and not results:
                st.markdown(f"<div class='response-box'>{explanation}</div>", unsafe_allow_html=True)

            if results and "data" in results:
                df = pd.DataFrame(results["data"], columns=results["columns"])
                st.dataframe(df, width="stretch")

        else:
            st.markdown(f"<div class='response-box'>{answer}</div>", unsafe_allow_html=True)

    else:
        st.warning("Por favor, digite uma pergunta.")