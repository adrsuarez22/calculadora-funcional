"""Prueba de la capa de persistencia, con un cliente Supabase simulado.

No requiere credenciales ni conexión: sustituye el cliente real por uno
en memoria y comprueba la normalización del código de paciente, el
registro construido y el cálculo de deltas del historial.

    python3 test_persistencia.py
"""
import sys, types, pandas as pd
from datetime import date

# Stub mínimo de streamlit: solo se usa cache_resource en este bloque.
st = types.ModuleType("streamlit")
st.cache_resource = lambda **kw: (lambda f: f)
st.secrets = {}

# app.py es un script único de Streamlit, así que en lugar de importarlo
# (lo que ejecutaría toda la interfaz) se extrae y ejecuta solo el bloque
# de persistencia, delimitado por sus cabeceras de sección.
fuente = open("app.py", encoding="utf-8").read()
try:
    bloque = fuente.split("# Persistencia (Supabase)")[1].split("# Carga de datos")[0]
    bloque = bloque.split("# =========================")[1]
except IndexError:
    sys.exit("No se encontró el bloque de persistencia en app.py: "
             "¿cambiaron las cabeceras de sección?")
ns = {"st": st, "pd": pd, "date": date}
exec(bloque, ns)

fallos = []
def check(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print(f"{'PASA' if ok else 'FALLA'}  {nombre}: {obtenido!r}")
    if not ok:
        fallos.append(f"{nombre}: esperado {esperado!r}, obtenido {obtenido!r}")

# --- Normalización del código de paciente ---
n = ns["normalizar_codigo_paciente"]
check("normaliza espacios y mayusculas", n("  hc-1042 "), "HC-1042")
check("colapsa espacios internos", n("hc  1042"), "HC 1042")
check("codigo vacio", n("   "), "")

# --- Cliente simulado ---
class TablaFalsa:
    def __init__(self, almacen): self.almacen, self.filtros, self.orden = almacen, {}, None
    def insert(self, registro): self.pendiente = registro; return self
    def select(self, _cols): return self
    def eq(self, col, val): self.filtros[col] = val; return self
    def order(self, col, desc=False): self.orden = (col, desc); return self
    def execute(self):
        if hasattr(self, "pendiente"):
            self.almacen.append(self.pendiente); return types.SimpleNamespace(data=[self.pendiente])
        filas = [f for f in self.almacen
                 if all(f.get(c) == v for c, v in self.filtros.items())]
        if self.orden: filas = sorted(filas, key=lambda f: f[self.orden[0]], reverse=self.orden[1])
        return types.SimpleNamespace(data=filas)

class ClienteFalso:
    def __init__(self): self.almacen = []
    def table(self, _n): return TablaFalsa(self.almacen)

cliente = ClienteFalso()
ns["obtener_cliente_supabase"] = lambda: (cliente, None)

guardar, historial_de, deltas, fmt = (ns["guardar_evaluacion"], ns["obtener_historial"],
                                      ns["calcular_deltas"], ns["formatear_delta"])

# --- Guardado ---
ok, err = guardar(codigo_paciente=" hc-1042 ", prueba="Caminata 6 minutos", valor_medido=420,
                  unidad="m", percentil=17.4321, clasificacion="Bajo", edad=70,
                  estrato="altura 160 cm · edad 70 años", sexo=None, observaciones="  basal  ")
check("guardado correcto", (ok, err), (True, None))
reg = cliente.almacen[0]
check("codigo normalizado al guardar", reg["codigo_paciente"], "HC-1042")
check("percentil redondeado a 1 decimal", reg["percentil"], 17.4)
check("sexo NULL en caminata", reg["sexo"], None)
check("observaciones sin espacios", reg["observaciones"], "basal")
check("fecha de hoy", reg["fecha"], date.today().isoformat())

# Percentil no estimable -> NULL, no un número inventado
guardar(codigo_paciente="HC-1042", prueba="Fuerza prensión", valor_medido=99, unidad="kg",
        percentil=None, clasificacion="Sin clasificación", edad=70, estrato="mujer · 70-74 años", sexo="mujer")
check("percentil no estimable se guarda NULL", cliente.almacen[1]["percentil"], None)

# Código vacío se rechaza antes de tocar la base
ok2, err2 = guardar(codigo_paciente="   ", prueba="Caminata 6 minutos", valor_medido=1, unidad="m",
                    percentil=50, clasificacion="Normal", edad=70, estrato="x")
check("rechaza codigo vacio", (ok2, err2), (False, "Falta el código de paciente."))
check("no escribio la fila rechazada", len(cliente.almacen), 2)

# --- Historial y deltas: dos visitas de la misma prueba ---
guardar(codigo_paciente="HC-1042", prueba="Caminata 6 minutos", valor_medido=468, unidad="m",
        percentil=31.0, clasificacion="Normal", edad=71, estrato="altura 160 cm · edad 70 años")
guardar(codigo_paciente="OTRO-99", prueba="Caminata 6 minutos", valor_medido=300, unidad="m",
        percentil=3.0, clasificacion="Muy bajo", edad=80, estrato="x")

df, err3 = historial_de(" hc-1042 ")
check("historial solo del paciente pedido", len(df), 3)
check("no filtra otros pacientes", "OTRO-99" not in str(df.values), True)

d = deltas(df)
cam = d[d["prueba"] == "Caminata 6 minutos"].reset_index(drop=True)
check("primera visita sin delta", pd.isna(cam.loc[0, "delta_valor"]), True)
check("delta de valor entre visitas", cam.loc[1, "delta_valor"], 48.0)
check("delta de percentil entre visitas", round(cam.loc[1, "delta_percentil"], 1), 13.6)
check("delta no cruza pruebas distintas",
      bool(pd.isna(d[d["prueba"] == "Fuerza prensión"]["delta_valor"].iloc[0])), True)

check("formato delta positivo", fmt(48.0), "+48.0")
check("formato delta negativo", fmt(-12.5), "-12.5")
check("formato delta ausente", fmt(float("nan")), "—")

print()
if fallos:
    print(f"*** {len(fallos)} FALLOS ***"); [print(" -", f) for f in fallos]; sys.exit(1)
print("Todas las comprobaciones pasan.")

# --- Construcción de la tabla del historial (misma lógica que la UI) ---
def formatear_percentil(p):
    return str(int(p)) if float(p).is_integer() else f"{p:.1f}"

tabla = pd.DataFrame({
    "Fecha": d["fecha"],
    "Prueba": d["prueba"],
    "Resultado": [f"{v:.1f} {u}" for v, u in zip(d["valor_medido"], d["unidad"])],
    "Δ resultado": [fmt(x) for x in d["delta_valor"]],
    "Percentil": ["N/D" if pd.isna(p) else f"P{formatear_percentil(p)}" for p in d["percentil"]],
    "Δ percentil": [fmt(x) for x in d["delta_percentil"]],
    "Clasificación": d["clasificacion"],
    "Observaciones": d["observaciones"].fillna(""),
})
print()
print(tabla.to_string(index=False))
