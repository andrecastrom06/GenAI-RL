import streamlit as st
from main import agent_loop

st.title("Agente de Consultas SQL com Gemini")

user_query = st.text_input("Digite sua pergunta sobre o banco de dados:")

if st.button("Consultar"):
    if user_query:
        print(f"[Streamlit] Usuário enviou pergunta: {user_query}")
        answer = agent_loop(user_query)
        print(f"[Streamlit] Resposta recebida: {answer}")
        st.write("Resposta:")
        st.text(answer)
    else:
        st.write("Por favor, digite uma pergunta.")