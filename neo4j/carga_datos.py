from neo4j import GraphDatabase
import random

# ==========================
# CONEXION
# ==========================

URI = "neo4j://127.0.0.1:7687"
USUARIO = "neo4j"
PASSWORD = "Datos2026"

driver = GraphDatabase.driver(
    URI,
    auth=(USUARIO, PASSWORD)
)

# ==========================
# LIMPIEZA
# ==========================

with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")

print("Base Neo4j limpiada")

# ==========================
# PERSONAS
# ==========================

with driver.session() as session:

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

        session.run("""
            CREATE (:Persona {
                persona_id: $id,
                nombre: $nombre,
                tipo: $tipo
            })
        """,
        id=f"P{i}",
        nombre=f"Persona {i}",
        tipo=tipo)

print("300 personas cargadas")


# ==========================
# EXPEDIENTES
# ==========================

with driver.session() as session:

    for i in range(1, 201):

        session.run("""
            CREATE (:Expediente {
                expediente_id: $id,
                caratula: $caratula,
                estado: $estado
            })
        """,
        id=f"EXP{i}",
        caratula=f"Causa {i}",
        estado="en proceso" if i % 2 == 0 else "cerrado")

print("200 expedientes cargados")



# ==========================
# RELACIONES PERSONA - EXPEDIENTE
# ==========================

with driver.session() as session:

    for i in range(1, 201):

        imputado_id = f"P{(i % 120) + 1}"
        abogado_id = f"P{121 + (i % 80)}"
        expediente_id = f"EXP{i}"

        # Imputado interviene en expediente
        session.run("""
            MATCH (p:Persona {persona_id: $persona_id})
            MATCH (e:Expediente {expediente_id: $expediente_id})
            CREATE (p)-[:INTERVIENE_EN]->(e)
        """,
        persona_id=imputado_id,
        expediente_id=expediente_id)

        # Abogado interviene en expediente
        session.run("""
            MATCH (p:Persona {persona_id: $persona_id})
            MATCH (e:Expediente {expediente_id: $expediente_id})
            CREATE (p)-[:INTERVIENE_EN]->(e)
        """,
        persona_id=abogado_id,
        expediente_id=expediente_id)

print("Relaciones INTERVIENE_EN cargadas")


# ==========================
# RELACIONES REPRESENTA
# ==========================

with driver.session() as session:

    for i in range(1, 101):

        abogado_id = f"P{121 + (i % 80)}"
        imputado_id = f"P{(i % 120) + 1}"

        session.run("""
            MATCH (a:Persona {persona_id: $abogado})
            MATCH (i:Persona {persona_id: $imputado})
            CREATE (a)-[:REPRESENTA]->(i)
        """,
        abogado=abogado_id,
        imputado=imputado_id)

print("100 relaciones REPRESENTA cargadas")


# ==========================
# RELACIONES CAUSAS CONEXAS
# ==========================

with driver.session() as session:

    for i in range(1, 51):

        expediente_1 = f"EXP{i}"
        expediente_2 = f"EXP{i + 1}"

        session.run("""
            MATCH (e1:Expediente {expediente_id: $expediente_1})
            MATCH (e2:Expediente {expediente_id: $expediente_2})
            CREATE (e1)-[:CONEXO_A {
                tipo: "mismo_imputado"
            }]->(e2)
        """,
        expediente_1=expediente_1,
        expediente_2=expediente_2)

print("50 relaciones CONEXO_A cargadas")