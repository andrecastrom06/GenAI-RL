import streamlit as st
import pandas as pd
from main import agent_loop

st.set_page_config(page_title="E-commerce Rocket Lab AI", layout="wide")

# CSS
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #031d12, #062d1a);
    color: #e8f5e9;
    font-family: 'Inter', sans-serif;
}

/* HEADER */
.header {
    text-align: center;
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 25px;
    color: #e8f5e9;
    text-shadow: 0 0 10px rgba(102, 187, 106, 0.5);
}

/* SEARCH CONTAINER */
.search-container {
    background: rgba(255,255,255,0.05);
    padding: 10px;
    border-radius: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
}

/* INPUT */
.stTextInput input {
    background: transparent !important;
    border: none !important;
    color: white !important;
    font-size: 16px;
}

/* BOTÃO */
.stButton>button {
    background: linear-gradient(90deg, #43a047, #66bb6a);
    border-radius: 15px;
    padding: 10px 20px;
    border: none;
    font-weight: 600;
    color: #012b16;
    transition: 0.2s;
}
.stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0 0 15px rgba(102,187,106,0.6);
}

/* CARDS */
.card {
    background: rgba(255,255,255,0.04);
    padding: 20px;
    border-radius: 18px;
    margin-top: 20px;
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.08);
}

/* TITULOS */
.section-title {
    font-size: 12px;
    color: #81c784;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)

# Titulo
st.markdown("<div class='header'>🧠 E-commerce Rocket Lab AI</div>", unsafe_allow_html=True)

# Barra de pesquisa
st.markdown("<div class='search-container'>", unsafe_allow_html=True)

col1, col2 = st.columns([5,1])

with col1:
    user_query = st.text_input(
        "",
        placeholder="Ex: produto pior vendido, faturamento mensal..."
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    consultar = st.button("Analisar")

st.markdown("</div>", unsafe_allow_html=True)

# Execução da query e exibição dos resultados
if consultar and user_query:
    with st.spinner("Analisando dados..."):
        answer = agent_loop(user_query)

    if isinstance(answer, dict):
        explanation = answer.get("explanation", "")
        results = answer.get("results")

        if explanation:
            st.markdown(f"""
            <div class="card">
                <div class="section-title">Insights da IA</div>
                <div style="font-size:16px; line-height:1.6;">
                    {explanation}
                </div>
            </div>
            """, unsafe_allow_html=True)

        if results and "data" in results:
            df = pd.DataFrame(results["data"], columns=results["columns"])

            st.markdown("""
            <div class="card">
                <div class="section-title">Dados</div>
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(df, use_container_width=True)

    else:
        st.markdown(f"""
        <div class="card">
            {answer}
        </div>
        """, unsafe_allow_html=True)

elif consultar:
    st.warning("Digite uma pergunta primeiro.")