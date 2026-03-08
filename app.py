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

    # Fallback por posición:
    # col 0 = edad
    # col 1 = altura
    # col 2 = percentil
    # col 3 = distancia
    col_edad = buscar_columna(df, ["edad", "edad_anos", "anos", "age"], fallback_index=0)
    col_altura = buscar_columna(df, ["altura", "altura_cm", "talla", "height"], fallback_index=1)
    col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=2)
    col_resultado = buscar_columna(df, ["distancia", "distancia_m", "metros", "resultado"], fallback_index=3)

    df = convertir_numerico(df, [col_edad, col_altura, col_percentil, col_resultado])
    df = df.dropna(subset=[col_edad, col_altura, col_percentil, col_resultado])

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

    # Fallback por posición:
    # col 0 = edad
    # col 1 = sexo
    # col 2 = percentil
    # col 3 = fuerza
    col_edad = buscar_columna(df, ["edad", "edad_anos", "anos", "age"], fallback_index=0)
    col_sexo = buscar_columna(df, ["sexo", "genero", "sex"], fallback_index=1)
    col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=2)
    col_resultado = buscar_columna(df, ["fuerza", "fuerza_kg", "kg", "prension", "prension_kg"], fallback_index=3)

    df = convertir_numerico(df, [col_edad, col_percentil, col_resultado])
    df[col_sexo] = normalizar_sexo_serie(df[col_sexo])
    df = df.dropna(subset=[col_edad, col_percentil, col_resultado])

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

    columnas = list(df.columns)

    # Posibles estructuras:
    # A) sexo, grupoedad, percentil, repeticiones
    # B) sexo, percentil, repeticiones
    col_sexo = buscar_columna(df, ["sexo", "genero", "sex"], fallback_index=0)
    col_grupo = buscar_columna(df, ["grupoedad", "grupo_edad", "grupo", "ag"], fallback_index=1, obligatoria=False)

    # Detectar si la segunda columna realmente parece grupo AG1..AG5
    if col_grupo is not None:
        valores_grupo = df[col_grupo].astype(str).str.upper().str.strip()
        if not valores_grupo.str.startswith("AG").any():
            col_grupo = None

    if col_grupo is not None:
        col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=2)
        col_resultado = buscar_columna(df, ["repeticiones", "resultado", "levantadas"], fallback_index=3)
    else:
        col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=1)
        col_resultado = buscar_columna(df, ["repeticiones", "resultado", "levantadas"], fallback_index=2)

    df = convertir_numerico(df, [col_percentil, col_resultado])
    df[col_sexo] = normalizar_sexo_serie(df[col_sexo])

    if col_grupo is not None:
        df[col_grupo] = df[col_grupo].astype(str).str.upper().str.strip()

    df = df.dropna(subset=[col_percentil, col_resultado])

    return df, {
        "sexo": col_sexo,
        "grupo": col_grupo,
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
    percentiles = sorted(df[cols["percentil"]].dropna().astype(int).unique().tolist())

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

    edades = sorted(df[cols["edad"]].dropna().astype(int).unique().tolist())
    percentiles = sorted(df[cols["percentil"]].dropna().astype(int).unique().tolist())

    sexo_ui = st.selectbox("Sexo", ["Hombre", "Mujer"])
    edad = st.selectbox("Edad", edades)
    percentil = st.selectbox("Percentil", percentiles)

    sexo = formatear_sexo_ui(sexo_ui)

    resultado = df[
        (df[cols["edad"]] == edad) &
        (df[cols["sexo"]] == sexo) &
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

    percentiles = sorted(df[cols["percentil"]].dropna().astype(int).unique().tolist())
    percentil = st.selectbox("Percentil", percentiles)

    if cols["grupo"] is not None:
        edad = st.number_input("Edad", min_value=65, max_value=100, value=70, step=1)
        grupo = edad_a_grupo(edad)

        if grupo is None:
            st.warning("Para esta prueba la edad debe ser 65 o más.")
        else:
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
    else:
        resultado = df[
            (df[cols["sexo"]] == sexo) &
            (df[cols["percentil"]] == percentil)
        ]

        if not resultado.empty:
            valor = resultado.iloc[0][cols["resultado"]]
            st.success(f"Repeticiones esperadas: {valor}")
        else:
            st.warning("No hay un valor exacto para esa combinación.")
