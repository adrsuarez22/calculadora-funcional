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


def buscar_columna(df, candidatos, fallback_index=None, obligatoria=True):
    columnas = list(df.columns)
    columnas_set = set(columnas)

    for c in candidatos:
        c_norm = normalizar_texto(c)
        if c_norm in columnas_set:
            return c_norm

    if fallback_index is not None and len(columnas) > fallback_index:
        return columnas[fallback_index]

    if obligatoria:
        raise ValueError(
            f"No se encontró ninguna de estas columnas: {candidatos}. "
            f"Columnas disponibles: {columnas}"
        )
    return None


def convertir_numerico(df, columnas):
    for c in columnas:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def normalizar_sexo_serie(serie):
    return (
        serie.astype(str)
        .str.strip()
        .str.lower()
        .replace({
            "hombres": "hombre",
            "mujeres": "mujer",
            "male": "hombre",
            "female": "mujer",
            "m": "hombre",
            "f": "mujer"
        })
    )


@st.cache_data
def cargar_caminata():
    df = pd.read_csv("caminata_6min_long.csv")
    df = normalizar_columnas(df)

    # Orden real del CSV:
    # altura_cm, edad_anos, percentil, distancia_m, unidad, fuente
    col_altura = buscar_columna(df, ["altura_cm", "altura", "talla", "height"], fallback_index=0)
    col_edad = buscar_columna(df, ["edad_anos", "edad", "anos", "age"], fallback_index=1)
    col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=2)
    col_resultado = buscar_columna(df, ["distancia_m", "distancia", "metros", "resultado"], fallback_index=3)

    df = convertir_numerico(df, [col_altura, col_edad, col_percentil, col_resultado])
    df = df.dropna(subset=[col_altura, col_edad, col_percentil, col_resultado])

    return df, {
        "altura": col_altura,
        "edad": col_edad,
        "percentil": col_percentil,
        "resultado": col_resultado
    }


@st.cache_data
def cargar_prension():
    df = pd.read_csv("prension_manual_long.csv")
    df = normalizar_columnas(df)

    # Orden real del CSV:
    # sexo, edad_rango, percentil, fuerza_kg, unidad, fuente
    col_sexo = buscar_columna(df, ["sexo", "genero", "sex"], fallback_index=0)
    col_edad = buscar_columna(df, ["edad_rango", "edad", "edad_anos", "anos", "age"], fallback_index=1)
    col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=2)
    col_resultado = buscar_columna(df, ["fuerza_kg", "fuerza", "kg", "prension", "prension_kg"], fallback_index=3)

    df[col_sexo] = normalizar_sexo_serie(df[col_sexo])
    df = convertir_numerico(df, [col_percentil, col_resultado])
    df = df.dropna(subset=[col_percentil, col_resultado])

    return df, {
        "sexo": col_sexo,
        "edad": col_edad,
        "percentil": col_percentil,
        "resultado": col_resultado
    }


@st.cache_data
def cargar_silla():
    df = pd.read_csv("silla_long.csv")
    df = normalizar_columnas(df)

    # Orden real del CSV:
    # sexo, grupo_edad, edad_rango, n_muestra, percentil, valor_repeticiones, fuente
    col_sexo = buscar_columna(df, ["sexo", "genero", "sex"], fallback_index=0)
    col_grupo = buscar_columna(df, ["grupo_edad", "grupoedad", "grupo", "ag"], fallback_index=1)
    col_edad_rango = buscar_columna(df, ["edad_rango", "edad", "rango_edad"], fallback_index=2, obligatoria=False)
    col_n = buscar_columna(df, ["n_muestra", "n", "muestra"], fallback_index=3, obligatoria=False)
    col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=4)
    col_resultado = buscar_columna(df, ["valor_repeticiones", "repeticiones", "resultado", "levantadas"], fallback_index=5)

    df[col_sexo] = normalizar_sexo_serie(df[col_sexo])
    df[col_grupo] = df[col_grupo].astype(str).str.strip().str.upper()
    df = convertir_numerico(df, [col_percentil, col_resultado])
    df = df.dropna(subset=[col_percentil, col_resultado])

    return df, {
        "sexo": col_sexo,
        "grupo": col_grupo,
        "edad_rango": col_edad_rango,
        "n": col_n,
        "percentil": col_percentil,
        "resultado": col_resultado
    }


def formatear_sexo_ui(valor):
    v = str(valor).strip().lower()
    if v == "hombre":
        return "hombre"
    if v == "mujer":
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

    edades = sorted(df[cols["edad"]].dropna().astype(int).unique().tolist())
    alturas = sorted(df[cols["altura"]].dropna().astype(int).unique().tolist())
    percentiles = sorted(df[cols["percentil"]].dropna().unique().tolist())

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

    sexos = ["Hombre", "Mujer"]
    edades = sorted(df[cols["edad"]].dropna().astype(str).unique().tolist())
    percentiles = sorted(df[cols["percentil"]].dropna().unique().tolist())

    sexo_ui = st.selectbox("Sexo", sexos)
    edad = st.selectbox("Edad", edades)
    percentil = st.selectbox("Percentil", percentiles)

    sexo = formatear_sexo_ui(sexo_ui)

    resultado = df[
        (df[cols["sexo"]] == sexo) &
        (df[cols["edad"]].astype(str) == str(edad)) &
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
    sexo = formatear_sexo_ui(sexo_ui)

    edad = st.number_input("Edad", min_value=65, max_value=100, value=70, step=1)
    grupo = edad_a_grupo(edad)

    percentiles = sorted(df[cols["percentil"]].dropna().unique().tolist())
    percentil = st.selectbox("Percentil", percentiles)

    resultado = df[
        (df[cols["sexo"]] == sexo) &
        (df[cols["grupo"]] == grupo) &
        (df[cols["percentil"]] == percentil)
    ]

    if not resultado.empty:
        valor = resultado.iloc[0][cols["resultado"]]
        st.success(f"Repeticiones esperadas: {valor}")
        st.caption(f"Grupo de edad utilizado: {grupo}")
    else:
        st.warning("No hay un valor exacto para esa combinación.")
