-- =====================================================================
-- Calculadora de Condición Física — esquema de persistencia
--
-- Ejecutar una vez en el SQL Editor del proyecto de Supabase.
--
-- Principio de diseño: la tabla NO contiene datos identificativos
-- directos. `codigo_paciente` es un seudónimo asignado por el
-- profesional; la correspondencia código <-> persona vive en la
-- historia clínica, fuera de esta base de datos.
-- =====================================================================

create table if not exists public.evaluaciones (
    id              bigint generated always as identity primary key,
    creado_en       timestamptz  not null default now(),

    fecha           date         not null,
    codigo_paciente text         not null,

    prueba          text         not null
                    check (prueba in ('Caminata 6 minutos',
                                      'Fuerza prensión',
                                      'Levantarse de silla')),

    valor_medido    double precision not null check (valor_medido >= 0),
    unidad          text         not null,

    -- NULL cuando el valor cae fuera del rango tabulado y no pudo
    -- estimarse un percentil. Preferimos el hueco explícito a un número
    -- inventado.
    percentil       double precision check (percentil between 0 and 100),
    clasificacion   text,

    edad            integer      not null check (edad between 0 and 120),

    -- NULL en la caminata de 6 minutos: esa normativa estratifica por
    -- altura y edad, no por sexo.
    sexo            text         check (sexo in ('hombre', 'mujer')),

    estrato         text,
    observaciones   text
);

comment on table  public.evaluaciones          is 'Evaluaciones funcionales seudonimizadas.';
comment on column public.evaluaciones.codigo_paciente is 'Seudónimo. Nunca nombre, DNI ni dato identificativo directo.';
comment on column public.evaluaciones.percentil       is 'NULL si el valor quedó fuera del rango normativo tabulado.';
comment on column public.evaluaciones.sexo            is 'NULL en la caminata de 6 min (normativa no estratificada por sexo).';

-- El historial siempre se consulta por paciente y se ordena por fecha.
create index if not exists evaluaciones_codigo_fecha_idx
    on public.evaluaciones (codigo_paciente, fecha);


-- =====================================================================
-- Row Level Security
--
-- Supabase expone la tabla vía API REST. SIN RLS, cualquiera con la
-- clave anónima puede leer y escribir todas las evaluaciones. Se activa
-- por defecto y se deja SIN políticas: así la tabla queda cerrada hasta
-- que se decida conscientemente quién accede.
-- =====================================================================

alter table public.evaluaciones enable row level security;

-- Opción A — despliegue con autenticación de Supabase (recomendado).
-- Cada profesional accede solo a lo que él mismo registró. Requiere
-- añadir la columna de propietario y usar el login de Supabase en la app:
--
--   alter table public.evaluaciones
--       add column if not exists propietario uuid not null default auth.uid();
--
--   create policy "propietario lee lo suyo" on public.evaluaciones
--       for select using (auth.uid() = propietario);
--
--   create policy "propietario inserta lo suyo" on public.evaluaciones
--       for insert with check (auth.uid() = propietario);

-- Opción B — instalación local de un solo profesional, sin login.
-- Solo es aceptable si la app corre en el equipo del profesional y la
-- service_role key NUNCA se publica. No usar en un despliegue accesible
-- desde internet:
--
--   create policy "acceso completo autenticado" on public.evaluaciones
--       for all to authenticated using (true) with check (true);
