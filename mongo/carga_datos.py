from pymongo import MongoClient
from datetime import datetime
import random

# ==========================
# CONEXIÓN
# ==========================

client = MongoClient("mongodb://localhost:27017/")
db = client["sistema_judicial"]

# ==========================
# LIMPIEZA
# ==========================

db.personas.delete_many({})
db.expedientes.delete_many({})
db.actuaciones.delete_many({})
db.audiencias.delete_many({})
db.resoluciones.delete_many({})

print("Base limpiada")

# ==========================
# PERSONAS
# ==========================

personas = []

for i in range(1, 301):

    if i <= 120:
        tipo = "imputado"
    elif i <= 200:
        tipo = "abogado"
    elif i <= 240:
        tipo = "victima"
    elif i <= 270:
        tipo = "testigo"
    elif i <= 290:
        tipo = "perito"
    elif i <= 295:
        tipo = "fiscal"
    else:
        tipo = "juez"

    personas.append({
        "persona_id": f"P{i}",
        "nombre": f"Persona {i}",
        "dni": str(30000000 + i),
        "tipo": tipo,
        "domicilio": "Buenos Aires"
    })

db.personas.insert_many(personas)

print("300 personas cargadas")

# ==========================
# EXPEDIENTES
# ==========================

fueros = ["penal", "civil", "laboral"]

expedientes = []

for i in range(1, 201):

    expedientes.append({

        "expediente_id": f"EXP{i}",

        "caratula": f"Causa {i}",

        "fuero": random.choice(fueros),

        "juzgado": f"Juzgado {(i % 10) + 1}",

        "fecha_inicio": datetime(
            2020 + (i % 5),
            (i % 12) + 1,
            (i % 28) + 1
        ),

        "estado": random.choice([
            "en proceso",
            "cerrado"
        ]),

        "objeto": f"Objeto del proceso {i}",

        "imputados": [
            f"P{random.randint(1,120)}"
        ],

        "abogados": [
            f"P{random.randint(121,200)}"
        ]
    })

db.expedientes.insert_many(expedientes)

print("200 expedientes cargados")

print("Carga inicial finalizada")
