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

La app abre en `http://localhost:8501`. **Para calcular percentiles no requiere
configuración alguna**: las tablas normativas son los CSV del repositorio. El registro
de evaluaciones es una función opcional que se activa con credenciales de Supabase (ver
más abajo); sin ellas, todo lo demás funciona igual.

---

## Estructura del repositorio

```
app.py                          Aplicación completa (UI + estimación + persistencia)
caminata_6min_long.csv          Normativa 6MWT   — altura × edad × percentil
prension_manual_long.csv        Normativa fuerza — sexo × rango etario × percentil
silla_long.csv                  Normativa silla  — sexo × grupo etario × percentil
supabase_schema.sql             Esquema de la tabla de evaluaciones + RLS
test_persistencia.py            Pruebas de la capa de persistencia
.streamlit/secrets.toml.example Plantilla de credenciales (la real no se versiona)
requirements.txt                Dependencias
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
## Registro de evaluaciones y seguimiento

La aplicación puede registrar cada evaluación en [Supabase](https://supabase.com/)
para seguir la **evolución de un paciente entre visitas**, que es el valor real de
persistir: un percentil aislado describe un momento; la serie describe una trayectoria.

Es **opcional**. Sin credenciales configuradas la calculadora funciona íntegra y solo
se desactiva el guardado, indicando el motivo en la barra lateral.

### Pseudonimización

El único identificador que se almacena es un **código de paciente** asignado por el
profesional (`HC-1042`, por ejemplo). La aplicación no pide ni guarda nombre, DNI ni
ningún dato identificativo directo: **la correspondencia entre código y persona debe
quedar en la historia clínica, fuera de esta base de datos.**

El código se normaliza a mayúsculas y sin espacios sobrantes, de modo que `hc-1042`,
`HC-1042 ` y `Hc-1042` son el mismo paciente y el historial no se fragmenta por
diferencias de tipeo.

### Puesta en marcha

1. Crear un proyecto en Supabase.
2. Ejecutar [`supabase_schema.sql`](supabase_schema.sql) en el SQL Editor. Crea la tabla
   `evaluaciones`, su índice y **activa Row Level Security sin políticas**: la tabla
   queda cerrada hasta que se decida conscientemente quién accede. El archivo incluye
   las dos políticas habituales, comentadas, con sus condiciones de uso.
3. Copiar `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completar
   `SUPABASE_URL` y `SUPABASE_KEY` con la clave **`anon`** del proyecto — no la
   `service_role`, que ignora todas las políticas de RLS.
4. `.streamlit/secrets.toml` está en `.gitignore`. No debe versionarse.

### Uso

- El **código de paciente** se introduce en la barra lateral y persiste al cambiar de
  prueba: en una misma visita se pueden registrar las tres.
- Tras cada resultado aparece **Registrar evaluación**, con un campo de observaciones
  opcional.
- El desplegable **Historial** muestra todas las evaluaciones del código, con una
  columna **Δ** que compara cada una con la anterior *de la misma prueba*.

La lectura clínica del Δ de percentil merece una nota: como el percentil se recalcula
contra la referencia de la edad actual, **mantener el percentil no es estancarse**.
Significa que el paciente envejece conservando su posición relativa, lo que en un
seguimiento longitudinal ya es un resultado.

### Qué se guarda

| Columna | Contenido |
|---|---|
| `fecha`, `creado_en` | Fecha de la evaluación y sello de inserción |
| `codigo_paciente` | Seudónimo. Nunca un dato identificativo directo |
| `prueba`, `valor_medido`, `unidad` | Test realizado y resultado bruto |
| `percentil`, `clasificacion` | Percentil estimado y franja del semáforo |
| `edad`, `sexo`, `estrato` | Datos de estratificación y estrato normativo aplicado |
| `observaciones` | Texto libre opcional |

Dos campos son deliberadamente anulables:

- **`percentil` es `NULL`** cuando el valor cae fuera del rango tabulado y no pudo
  estimarse. Preferimos el hueco explícito a un número inventado.
- **`sexo` es `NULL`** en la caminata de 6 minutos, porque esa normativa estratifica por
  altura y edad, no por sexo. Registrarlo igual sería sugerir un ajuste que no existe.

### Pruebas

```bash
python3 test_persistencia.py
```

Sustituye el cliente de Supabase por uno en memoria y comprueba la normalización del
código, el registro construido y el cálculo de deltas. No requiere credenciales ni red.

### Protección de datos

Registrar evaluaciones, aun seudonimizadas, constituye un **tratamiento de datos de
salud**. La pseudonimización y la RLS reducen el riesgo pero no eximen de resolver base
legal, información al paciente, control de acceso, plazo de conservación y ubicación del
servidor. Es una decisión del responsable del tratamiento, no del software.
