import streamlit as st
import pandas as pd
import unicodedata
import math

st.set_page_config(page_title="Calculadora de Aptitud Física", layout="centered")


# =========================
# Utilidades generales
# =========================
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


def formatear_sexo_ui(valor):
    v = str(valor).strip().lower()
    if v == "hombre":
        return "hombre"
    if v == "mujer":
        return "mujer"
    return v


def edad_a_grupo_silla(edad):
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


def parsear_rango_edad(texto):
    t = str(texto).strip().replace(" ", "")
    if "-" in t:
        partes = t.split("-")
        try:
            return int(partes[0]), int(partes[1])
        except:
            return None
    if t.startswith("+"):
        try:
            inicio = int(t[1:])
            return inicio, 999
        except:
            return None
    return None


def buscar_rango_edad_prension(edad, rangos_disponibles):
    for r in rangos_disponibles:
        parsed = parsear_rango_edad(r)
        if parsed is None:
            continue
        desde, hasta = parsed
        if desde <= edad <= hasta:
            return r
    return None


def formatear_percentil(p):
    if float(p).is_integer():
        return str(int(p))
    return str(p)


def describir_percentil_estimado(p):
    if p < 10:
        return "Muy bajo"
    elif p < 25:
        return "Bajo"
    elif p < 50:
        return "Por debajo de la media"
    elif p == 50:
        return "Promedio"
    elif p < 75:
        return "Por encima de la media"
    elif p < 90:
        return "Bueno"
    else:
        return "Muy bueno"


def estimar_percentil(valor_medido, df_ref, col_valor, col_percentil):
    """
    Devuelve:
    - percentil_estimado_num
    - texto_resultado
    - texto_rango
    """
    ref = df_ref[[col_valor, col_percentil]].dropna().copy()
    ref = ref.sort_values(by=col_valor).drop_duplicates(subset=[col_valor, col_percentil])

    if ref.empty:
        return None, "Sin datos de referencia.", None

    valores = ref[col_valor].tolist()
    percentiles = ref[col_percentil].tolist()

    # Exacto
    exactos = ref[ref[col_valor] == valor_medido]
    if not exactos.empty:
        p = float(exactos.iloc[0][col_percentil])
        return p, f"Percentil exacto: P{formatear_percentil(p)}", f"P{formatear_percentil(p)}"

    # Por debajo del mínimo
    if valor_medido < min(valores):
        p = float(percentiles[0])
        return p, f"Por debajo del percentil mínimo disponible.", f"< P{formatear_percentil(p)}"

    # Por encima del máximo
    if valor_medido > max(valores):
        p = float(percentiles[-1])
        return p, f"Por encima del percentil máximo disponible.", f"> P{formatear_percentil(p)}"

    # Entre dos percentiles
    for i in range(len(ref) - 1):
        v1 = float(ref.iloc[i][col_valor])
        v2 = float(ref.iloc[i + 1][col_valor])
        p1 = float(ref.iloc[i][col_percentil])
        p2 = float(ref.iloc[i + 1][col_percentil])

        if v1 <= valor_medido <= v2:
            if v2 == v1:
                p_est = p1
            else:
                p_est = p1 + ((valor_medido - v1) / (v2 - v1)) * (p2 - p1)

            texto = f"Percentil estimado: P{p_est:.1f}"
            rango = f"Entre P{formatear_percentil(p1)} y P{formatear_percentil(p2)}"
            return p_est, texto, rango

    return None, "No se pudo estimar el percentil.", None


# =========================
# Carga de datos
# =========================
@st.cache_data
def cargar_caminata():
    df = pd.read_csv("caminata_6min_long.csv")
    df = normalizar_columnas(df)

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

    col_sexo = buscar_columna(df, ["sexo", "genero", "sex"], fallback_index=0)
    col_edad = buscar_columna(df, ["edad_rango", "edad", "edad_anos", "anos", "age"], fallback_index=1)
    col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=2)
    col_resultado = buscar_columna(df, ["fuerza_kg", "fuerza", "kg", "prension", "prension_kg"], fallback_index=3)

    df[col_sexo] = normalizar_sexo_serie(df[col_sexo])
    df[col_edad] = df[col_edad].astype(str).str.strip()
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

    col_sexo = buscar_columna(df, ["sexo", "genero", "sex"], fallback_index=0)
    col_grupo = buscar_columna(df, ["grupo_edad", "grupoedad", "grupo", "ag"], fallback_index=1)
    col_percentil = buscar_columna(df, ["percentil", "percentil_ref", "p"], fallback_index=4)
    col_resultado = buscar_columna(df, ["valor_repeticiones", "repeticiones", "resultado", "levantadas"], fallback_index=5)

    df[col_sexo] = normalizar_sexo_serie(df[col_sexo])
    df[col_grupo] = df[col_grupo].astype(str).str.strip().str.upper()
    df = convertir_numerico(df, [col_percentil, col_resultado])
    df = df.dropna(subset=[col_percentil, col_resultado])

    return df, {
        "sexo": col_sexo,
        "grupo": col_grupo,
        "percentil": col_percentil,
        "resultado": col_resultado
    }


# =========================
# Interfaz
# =========================
st.title("Calculadora de Aptitud Física")

prueba = st.selectbox(
    "Seleccionar prueba",
    ["Caminata 6 minutos", "Fuerza prensión", "Levantarse de silla"]
)

# -------------------------
# Caminata 6 minutos
# -------------------------
if prueba == "Caminata 6 minutos":
    df, cols = cargar_caminata()

    edades = sorted(df[cols["edad"]].dropna().astype(int).unique().tolist())
    alturas = sorted(df[cols["altura"]].dropna().astype(int).unique().tolist())

    edad = st.selectbox("Edad", edades)
    altura = st.selectbox("Altura (cm)", alturas)
    valor_medido = st.number_input("Distancia caminada (metros)", min_value=0.0, value=451.0, step=1.0)

    ref = df[
        (df[cols["edad"]] == edad) &
        (df[cols["altura"]] == altura)
    ].copy()

    if ref.empty:
        st.warning("No hay datos de referencia para esa combinación.")
    else:
        p50 = ref.loc[ref[cols["percentil"]] == 50, cols["resultado"]]
        p50_texto = f"{float(p50.iloc[0]):.0f} m" if not p50.empty else "No disponible"

        p_est, texto_p, rango_p = estimar_percentil(valor_medido, ref, cols["resultado"], cols["percentil"])

        if p_est is not None:
            st.success(texto_p)
            if rango_p:
                st.write(f"**Rango percentilar:** {rango_p}")
            st.write(f"**Referencia P50:** {p50_texto}")
            st.write(f"**Interpretación:** {describir_percentil_estimado(p_est)}")
        else:
            st.warning("No se pudo estimar el percentil.")


# -------------------------
# Fuerza prensión
# -------------------------
elif prueba == "Fuerza prensión":
    df, cols = cargar_prension()

    sexo_ui = st.selectbox("Sexo", ["Hombre", "Mujer"])
    sexo = formatear_sexo_ui(sexo_ui)

    edad = st.number_input("Edad", min_value=20, max_value=110, value=60, step=1)
    fuerza_medida = st.number_input("Fuerza medida (kg)", min_value=0.0, value=25.0, step=0.1)

    rangos = sorted(df[cols["edad"]].dropna().astype(str).unique().tolist())
    rango_edad = buscar_rango_edad_prension(edad, rangos)

    if rango_edad is None:
        st.warning("No hay un rango de edad válido para esa edad.")
    else:
        ref = df[
            (df[cols["sexo"]] == sexo) &
            (df[cols["edad"]].astype(str) == str(rango_edad))
        ].copy()

        if ref.empty:
            st.warning("No hay datos de referencia para esa combinación.")
        else:
            p50 = ref.loc[ref[cols["percentil"]] == 50, cols["resultado"]]
            p50_texto = f"{float(p50.iloc[0]):.1f} kg" if not p50.empty else "No disponible"

            p_est, texto_p, rango_p = estimar_percentil(fuerza_medida, ref, cols["resultado"], cols["percentil"])

            st.success(texto_p)
            if rango_p:
                st.write(f"**Rango percentilar:** {rango_p}")
            st.write(f"**Rango de edad utilizado:** {rango_edad}")
            st.write(f"**Referencia P50:** {p50_texto}")
            if p_est is not None:
                st.write(f"**Interpretación:** {describir_percentil_estimado(p_est)}")


# -------------------------
# Levantarse de silla
# -------------------------
elif prueba == "Levantarse de silla":
    df, cols = cargar_silla()

    sexo_ui = st.selectbox("Sexo", ["Hombre", "Mujer"])
    sexo = formatear_sexo_ui(sexo_ui)

    edad = st.number_input("Edad", min_value=65, max_value=110, value=70, step=1)
    repeticiones = st.number_input("Repeticiones realizadas", min_value=0.0, value=11.0, step=1.0)

    grupo = edad_a_grupo_silla(edad)

    if grupo is None:
        st.warning("No hay grupo etario válido para esa edad.")
    else:
        ref = df[
            (df[cols["sexo"]] == sexo) &
            (df[cols["grupo"]] == grupo)
        ].copy()

        if ref.empty:
            st.warning("No hay datos de referencia para esa combinación.")
        else:
            p50 = ref.loc[ref[cols["percentil"]] == 50, cols["resultado"]]
            p50_texto = f"{float(p50.iloc[0]):.0f}" if not p50.empty else "No disponible"

            p_est, texto_p, rango_p = estimar_percentil(repeticiones, ref, cols["resultado"], cols["percentil"])

            st.success(texto_p)
            if rango_p:
                st.write(f"**Rango percentilar:** {rango_p}")
            st.write(f"**Grupo de edad utilizado:** {grupo}")
            st.write(f"**Referencia P50:** {p50_texto} repeticiones")
            if p_est is not None:
                st.write(f"**Interpretación:** {describir_percentil_estimado(p_est)}")
