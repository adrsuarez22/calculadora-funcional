import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Calculadora de Aptitud Física", layout="centered")


def normalizar_texto(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.replace("(", "").replace(")", "")
    texto = texto.replace("%", "")
    texto = texto.replace(".", "").replace(",", "")
    texto = texto.replace("-", "_").replace("/", "_")
    texto = "_".join(texto.split())
    return texto


def normalizar_columnas(df):
    df = df.copy()
    df.columns = [normalizar_texto(c) for c in df.columns]
    return df


def buscar_columna(df, candidatos, obligatoria=True):
    cols = set(df.columns)
    for c in candidatos:
        c_norm = normalizar_texto(c)
        if c_norm in cols:
            return c_norm
    if obligatoria:
        raise ValueError(f"No se encontró ninguna de estas columnas: {candidatos}. Columnas disponibles: {list(df.columns)}")
    return None


def convertir_numerico(df, columnas):
    for c in columnas:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data
def cargar_caminata():
    df = pd.read_csv("caminata_6min_long.csv")
    df = normalizar_columnas(df)

    col_edad = buscar_columna(df, ["Edad", "edad"])
    col_altura = buscar_columna(df, ["Altura", "altura", "altura_cm", "altura_cm_"])
    col_percentil = buscar_columna(df, ["Percentil", "percentil", "p", "percentil_ref"])
    col_resultado = buscar_columna(df, ["Distancia", "distancia", "distancia_m", "metros"])

    df = convertir_numerico(df, [col_edad, col_altura, col_percentil, col_resultado])

    return df, {
        "edad": col_edad,
        "altura": col_altura,
        "percentil": col_percentil,
        "resultado": col_resultado
    }


@st.cache_data
def cargar_prension():
    df = pd.read_csv("prension_manual_long.csv")
    df = normalizar_columnas(df)

    col_edad = buscar_columna(df, ["Edad", "edad"])
    col_sexo = buscar_columna(df, ["Sexo", "sexo"])
    col_percentil = buscar_columna(df, ["Percentil", "percentil", "p", "percentil_ref"])
    col_resultado = buscar_columna(df, ["Fuerza", "fuerza", "fuerza_kg", "kg", "prension", "prension_kg"])

    df = convertir_numerico(df, [col_edad, col_percentil, col_resultado])
    df[col_sexo] = df[col_sexo].astype(str).str.strip().str.lower()

    return df, {
        "edad": col_edad,
        "sexo": col_sexo,
        "percentil": col_percentil,
        "resultado": col_resultado
    }


@st.cache_data
def cargar_silla():
    df = pd.read_csv("silla_long.csv")
    df = normalizar_columnas(df)

    col_sexo = buscar_columna(df, ["Sexo", "sexo"])
    col_percentil = buscar_columna(df, ["Percentil", "percentil", "p", "percentil_ref"])
    col_resultado = buscar_columna(df, ["Repeticiones", "repeticiones", "resultado", "levantadas"])
    col_grupo = buscar_columna(df, ["GrupoEdad", "grupo_edad", "grupo", "ag"], obligatoria=False)

    df = convertir_numerico(df, [col_percentil, col_resultado])
    df[col_sexo] = df[col_sexo].astype(str).str.strip().str.lower()

    if col_grupo:
        df[col_grupo] = df[col_grupo].astype(str).str.strip().str.upper()

    return df, {
        "sexo": col_sexo,
        "percentil": col_percentil,
        "resultado": col_resultado,
        "grupo": col_grupo
    }


def formatear_sexo(valor):
    v = str(valor).strip().lower()
    if v in ["hombre", "hombres", "male", "m"]:
        return "hombre"
    if v in ["mujer", "mujeres", "female", "f"]:
        return "mujer"
    return v


def edad_a_grupo(edad):
    if 65 <= edad <= 69:
        return "AG1"
    elif 70 <= edad <= 74:
        return "AG2"
    elif 75 <= edad <= 79:
        return "AG3"
    elif 80 <= edad <= 84:
        return "AG4"
    elif edad >= 85:
        return "AG5"
    return None


st.title("Calculadora de Aptitud Física")

prueba = st.selectbox(
    "Seleccionar prueba",
    ["Caminata 6 minutos", "Fuerza prensión", "Levantarse de silla"]
)

if prueba == "Caminata 6 minutos":
    df, cols = cargar_caminata()

    edades = sorted([int(x) for x in df[cols["edad"]].dropna().unique()])
    alturas = sorted([int(x) for x in df[cols["altura"]].dropna().unique()])
    percentiles = sorted([int(x) for x in df[cols["percentil"]].dropna().unique()])

    edad = st.selectbox("Edad", edades)
    altura = st.selectbox("Altura (cm)", alturas)
    percentil = st.selectbox("Percentil", percentiles)

    resultado = df[
        (df[cols["edad"]] == edad) &
        (df[cols["altura"]] == altura) &
        (df[cols["percentil"]] == percentil)
    ]

    if not resultado.empty:
        valor = resultado.iloc[0][cols["resultado"]]
        st.success(f"Distancia esperada: {valor} metros")
    else:
        st.warning("No hay un valor exacto para esa combinación.")


elif prueba == "Fuerza prensión":
    df, cols = cargar_prension()

    edades = sorted([int(x) for x in df[cols["edad"]].dropna().unique()])
    percentiles = sorted([int(x) for x in df[cols["percentil"]].dropna().unique()])

    sexo_ui = st.selectbox("Sexo", ["Hombre", "Mujer"])
    edad = st.selectbox("Edad", edades)
    percentil = st.selectbox("Percentil", percentiles)

    sexo = formatear_sexo(sexo_ui)

    resultado = df[
        (df[cols["edad"]] == edad) &
        (df[cols["sexo"]].apply(formatear_sexo) == sexo) &
        (df[cols["percentil"]] == percentil)
    ]

    if not resultado.empty:
        valor = resultado.iloc[0][cols["resultado"]]
        st.success(f"Fuerza esperada: {valor} kg")
    else:
        st.warning("No hay un valor exacto para esa combinación.")


elif prueba == "Levantarse de silla":
    df, cols = cargar_silla()

    sexo_ui = st.selectbox("Sexo", ["Hombre", "Mujer"])
    percentiles = sorted([int(x) for x in df[cols["percentil"]].dropna().unique()])
    percentil = st.selectbox("Percentil", percentiles)

    sexo = formatear_sexo(sexo_ui)

    if cols["grupo"] is not None:
        edad = st.number_input("Edad", min_value=65, max_value=100, value=70, step=1)
        grupo = edad_a_grupo(edad)

        if grupo is None:
            st.warning("Para esta prueba la edad debe ser 65 o más.")
        else:
            resultado = df[
                (df[cols["sexo"]].apply(formatear_sexo) == sexo) &
                (df[cols["grupo"]] == grupo) &
                (df[cols["percentil"]] == percentil)
            ]

            if not resultado.empty:
                valor = resultado.iloc[0][cols["resultado"]]
                st.success(f"Repeticiones esperadas: {valor}")
                st.caption(f"Grupo de edad utilizado: {grupo}")
            else:
                st.warning("No hay un valor exacto para esa combinación.")
    else:
        resultado = df[
            (df[cols["sexo"]].apply(formatear_sexo) == sexo) &
            (df[cols["percentil"]] == percentil)
        ]

        if not resultado.empty:
            valor = resultado.iloc[0][cols["resultado"]]
            st.success(f"Repeticiones esperadas: {valor}")
        else:
            st.warning("No hay un valor exacto para esa combinación.")
