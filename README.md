# Calculadora de Condición Física

Aplicación en [Streamlit](https://streamlit.io/) que convierte el resultado bruto de un
test de condición física en un **percentil poblacional**, con clasificación por semáforo
e interpretación clínica en lenguaje natural.

Responde la pregunta que realmente importa en consulta: no *"¿cuántos metros caminó?"*,
sino *"¿cuántos metros caminó **para alguien como ella**?"*.

---

## Pruebas implementadas

| Prueba | Unidad | Estratificación | Cobertura de la referencia |
|---|---|---|---|
| **Caminata de 6 minutos** (6MWT) | metros | altura × edad | Altura 150–190 cm (pasos de 10) · Edad 40–80 años (pasos de 10) · Percentiles 2.5, 10, 25, 50, 75, 90, 97.5 |
| **Fuerza de prensión manual** (dinamometría) | kg | sexo × rango etario | 20–24 años hasta 95–99 y `+100` · Percentiles 5, 10, 20…90, 95 |
| **Levantarse de la silla** (30-s chair stand) | repeticiones | sexo × grupo etario | AG1 (65–69) a AG5 (>84) · Percentiles 10, 20…90, 100 |

### Fuentes de las tablas normativas

| Prueba | Archivo | Referencia |
|---|---|---|
| Caminata 6 min | `caminata_6min_long.csv` | [PMC12408663](https://pmc.ncbi.nlm.nih.gov/articles/PMC12408663/) |
| Prensión manual | `prension_manual_long.csv` | [PMC11863340](https://pmc.ncbi.nlm.nih.gov/articles/PMC11863340/) |
| Levantarse de silla | `silla_long.csv` | [doi:10.1016/j.archger.2012.02.004](https://doi.org/10.1016/j.archger.2012.02.004) |

La cita viaja en la columna `fuente` de cada fila, de modo que cualquier valor mostrado
es trazable hasta su publicación de origen.

---

## Método de estimación del percentil

Implementado en `estimar_percentil()` (`app.py`). Para un valor medido `x` dentro del
estrato correspondiente al paciente:

1. **Coincidencia exacta** con un punto de corte tabulado → se devuelve ese percentil.
2. **`x` por debajo del corte mínimo** → se informa `< P<mínimo>`. No se extrapola.
3. **`x` por encima del corte máximo** → se informa `> P<máximo>`. No se extrapola.
4. **`x` entre dos cortes** `(v1, p1)` y `(v2, p2)` → **interpolación lineal**:

   ```
   p = p1 + ((x - v1) / (v2 - v1)) * (p2 - p1)
   ```

### Clasificación (semáforo)

| Percentil | Etiqueta | Color |
|---|---|---|
| < P10 | Muy bajo | Rojo |
| P10 – P25 | Bajo | Naranja |
| P25 – P75 | Normal | Verde |
| > P75 | Alto | Azul |

Cada franja tiene además un texto interpretativo específico por prueba
(`interpretar_clinicamente()`), redactado en términos de capacidad aeróbica, fuerza de
prensión o rendimiento funcional de miembros inferiores según corresponda.

### Limitaciones metodológicas

Conviene tenerlas presentes al leer un resultado:

- **La interpolación lineal es una aproximación.** La relación valor–percentil es
  marcadamente no lineal en las colas de la distribución; un P92 estimado entre P90 y
  P97.5 es menos preciso que un P50 estimado entre P40 y P60.
- **No hay interpolación entre estratos.** En la caminata de 6 minutos, edad y altura se
  eligen de listas discretas (40/50/…/80 años; 150/…/190 cm). Un paciente de 63 años y
  167 cm debe asignarse al estrato más cercano, con el sesgo que ello introduce.
- **Los valores fuera del rango tabulado no se extrapolan**, por diseño: se informa
  `< P2.5` o `> P97.5` en lugar de inventar un número.
- **Las poblaciones de referencia no son locales.** Los percentiles provienen de las
  cohortes descritas en las publicaciones citadas; su transferibilidad a otra población
  debe juzgarse clínicamente.
- Es una **herramienta de apoyo a la interpretación**, no un instrumento diagnóstico.

---

## Instalación y ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```

La app abre en `http://localhost:8501`. No requiere configuración, credenciales ni base
de datos: las tablas normativas son los CSV del repositorio.

---

## Estructura del repositorio

```
app.py                      Aplicación completa (UI + lógica de estimación)
caminata_6min_long.csv      Normativa 6MWT   — altura × edad × percentil
prension_manual_long.csv    Normativa fuerza — sexo × rango etario × percentil
silla_long.csv              Normativa silla  — sexo × grupo etario × percentil
requirements.txt            Dependencias
```

### Formato de los CSV

Los tres archivos están en formato *long*: **una fila por combinación
estrato–percentil–valor**, más las columnas `unidad` y `fuente`.

```csv
altura_cm,edad_anios,percentil,distancia_m,unidad,fuente
150,40,2.5,436,m,https://pmc.ncbi.nlm.nih.gov/articles/PMC12408663/
```

La lectura es tolerante a variaciones de encabezado: `normalizar_texto()` y
`buscar_columna()` resuelven acentos, mayúsculas, paréntesis, separadores y nombres
alternativos, con respaldo posicional. Para **añadir o actualizar una normativa** basta
con editar el CSV respetando el formato long — no hace falta tocar `app.py`.

---

## Persistencia de evaluaciones (no implementada)

La aplicación **no guarda** los datos que se introducen: cada cálculo es efímero y no se
registra información de pacientes en ningún lado.

Hubo un intento de integrar [Supabase](https://supabase.com/) (commit `18a18b8`) que
definió una función de guardado pero nunca llegó a invocarse desde la interfaz, y fue
revertido. La dependencia quedó huérfana en `requirements.txt` y se retiró.

Si se retoma, el esquema previsto para la tabla `evaluaciones` era:

| Columna | Tipo |
|---|---|
| `fecha` | date |
| `paciente` | text |
| `sexo` | text |
| `edad` | int |
| `prueba` | text |
| `valor_medido` | float |
| `percentilo` | float |
| `clasificacion` | text |

Reactivarlo requiere: volver a añadir `supabase` a `requirements.txt`, definir
`SUPABASE_URL` y `SUPABASE_KEY` en `.streamlit/secrets.toml`, **añadir un campo de
identificación de paciente a la interfaz** (hoy no existe) y llamar a la función de
guardado desde cada rama de prueba.

> Almacenar evaluaciones nominales convierte el proyecto en un tratamiento de datos de
> salud. Antes de activarlo corresponde resolver base legal, consentimiento,
> seudonimización, control de acceso y retención.
