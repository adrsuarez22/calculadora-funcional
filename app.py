import streamlit as st
import pandas as pd

st.title("Calculadora de Aptitud Física")

prueba = st.selectbox(
    "Seleccionar prueba",
    ["Caminata 6 minutos", "Fuerza prensión", "Levantarse de silla"]
)

edad = st.number_input("Edad", min_value=20, max_value=100, value=60)
sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])
altura = st.selectbox("Altura (cm)", [150,160,170,180,190])

percentil = st.selectbox("Percentil", [10,25,50,75,90])

if prueba == "Caminata 6 minutos":

    df = pd.read_csv("caminata_6min_long.csv")

    resultado = df[
        (df["Edad"] == edad) &
        (df["Altura"] == altura) &
        (df["Percentil"] == percentil)
    ]

    if not resultado.empty:
        st.success(f"Distancia esperada: {resultado.iloc[0]['Distancia']} metros")
    else:
        st.warning("No hay valor exacto en tabla")

if prueba == "Fuerza prensión":

    df = pd.read_csv("prension_manual_long.csv")

    resultado = df[
        (df["Edad"] == edad) &
        (df["Sexo"] == sexo) &
        (df["Percentil"] == percentil)
    ]

    if not resultado.empty:
        st.success(f"Fuerza esperada: {resultado.iloc[0]['Fuerza']} kg")

if prueba == "Levantarse de silla":

    df = pd.read_csv("silla_long.csv")

    resultado = df[
        (df["Sexo"] == sexo) &
        (df["Percentil"] == percentil)
    ]

    if not resultado.empty:
        st.success(f"Repeticiones esperadas: {resultado.iloc[0]['Repeticiones']}")