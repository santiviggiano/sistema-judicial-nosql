import redis
from datetime import datetime, timedelta

# ==========================
# CONEXION
# ==========================

r = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

# ==========================
# LIMPIEZA
# ==========================

r.flushdb()

print("Base Redis limpiada")



# ==========================
# SALAS (HASH)
# ==========================

for i in range(1, 4):

    r.hset(
        f"sala:{i}",
        mapping={
            "estado": "disponible",
            "juzgado": f"Juzgado {i}"
        }
    )

print("3 salas cargadas")



# ==========================
# AGENDA DEL DIA (SORTED SET)
# ==========================

audiencias_agenda = [
    ("EXP10", 1715000000),
    ("EXP20", 1715003600),
    ("EXP30", 1715007200),
    ("EXP40", 1715000000)  # mismo horario que EXP10 para simular solapamiento
]

for expediente_id, timestamp in audiencias_agenda:
    r.zadd("agenda:Juzgado1:20260601", {expediente_id: timestamp})

print("Agenda del día cargada")

# ==========================
# ACCESOS TEMPORALES
# ==========================

r.set(
    "acceso:EXP10:P131",
    "permitido",
    ex=7200,
    nx=True
)

r.set(
    "acceso:EXP20:P132",
    "permitido",
    ex=7200,
    nx=True
)

print("Accesos temporales cargados")


# ==========================
# NOTIFICACIONES (STREAM)
# ==========================

r.xadd(
    "notificaciones",
    {
        "evento": "inicio_audiencia",
        "expediente": "EXP10",
        "sala": "1"
    }
)

r.xadd(
    "notificaciones",
    {
        "evento": "fin_audiencia",
        "expediente": "EXP10",
        "sala": "1"
    }
)

r.xadd(
    "notificaciones",
    {
        "evento": "inicio_audiencia",
        "expediente": "EXP20",
        "sala": "2"
    }
)

print("Notificaciones cargadas")