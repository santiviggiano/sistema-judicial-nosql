from pymongo import MongoClient
import redis
from neo4j import GraphDatabase

# MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["sistema_judicial"]

# Redis
r = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

# Neo4j
neo4j_driver = GraphDatabase.driver(
    "neo4j://127.0.0.1:7687",
    auth=("neo4j", "Datos2026")
)

print("=" * 50)
print(" SISTEMA JUDICIAL POLIGLOTA ")
print("=" * 50)

while True:
    print("\nSeleccione una opción:")
    print("1 - Panel operativo del juzgado")
    print("2 - Apertura de audiencia")
    print("3 - Búsqueda de expediente y control de acceso")
    print("4 - Detección de conflicto de interés")
    print("5 - Cierre de audiencia")
    print("0 - Salir")

    opcion = input("\nOpción: ")

    if opcion == "1":
        print("\n[OP-1] Panel operativo del juzgado")

        print("\n=== SALAS ===")
        for sala in range(1, 4):
            datos = r.hgetall(f"sala:{sala}")
            if datos:
                print(f"Sala {sala} | Estado: {datos.get('estado', '-')}")

        print("\n=== AGENDA ===")
        agenda = r.zrange(
            "agenda:Juzgado1:20260601",
            0,
            -1,
            withscores=True
        )

        if agenda:
            for expediente, horario in agenda:
                print(f"{expediente} -> {int(horario)}")
        else:
            print("Sin audiencias pendientes")

        print("\n=== ULTIMAS NOTIFICACIONES ===")
        eventos = r.xrevrange("notificaciones", count=5)

        for evento_id, datos in eventos:
            print(
                f"{datos.get('evento')} | "
                f"{datos.get('expediente')} | "
                f"Sala {datos.get('sala')}"
            )

    elif opcion == "2":
        print("\n[OP-2] Apertura de audiencia")

        expediente_id = input("Expediente: ")
        sala = input("Sala: ")

        r.hset(
            f"sala:{sala}",
            mapping={
                "estado": "en_audiencia",
                "expediente_activo": expediente_id,
                "hora_fin_estimada": "18:00"
            }
        )

        r.zrem("agenda:Juzgado1:20260601", expediente_id)

        r.xadd(
            "notificaciones",
            {
                "evento": "inicio_audiencia",
                "expediente": expediente_id,
                "sala": sala
            }
        )

        with neo4j_driver.session() as session:
            resultado = session.run("""
                MATCH (e:Expediente {expediente_id: $expediente_id})-[:CONEXO_A*1..3]->(conexo:Expediente)
                RETURN conexo.expediente_id AS expediente_conexo
                LIMIT 5
            """, expediente_id=expediente_id)

            conexos = [record["expediente_conexo"] for record in resultado]

        db.actuaciones.insert_one({
            "actuacion_id": f"INICIO_AUDIENCIA_{expediente_id}",
            "expediente_id": expediente_id,
            "tipo": "inicio_audiencia",
            "autor": "sistema",
            "texto": f"Se inició la audiencia del expediente {expediente_id} en la sala {sala}"
        })

        print("\nAudiencia iniciada correctamente")
        print(f"Sala {sala} marcada como en_audiencia")
        print("Notificación enviada a Redis")
        print("Actuación registrada en MongoDB")

        if conexos:
            print("\nAdvertencia: existen causas conexas:")
            for c in conexos:
                print("-", c)
        else:
            print("\nNo se detectaron causas conexas")

    elif opcion == "3":
        print("\n[OP-3] Búsqueda de expediente y control de acceso")

        expediente_id = input("Expediente: ")
        operador_id = input("Operador: ")

        clave = f"acceso:{expediente_id}:{operador_id}"
        acceso = r.get(clave)

        if acceso:
            print("\nAcceso autorizado")

            expediente = db.expedientes.find_one(
                {"expediente_id": expediente_id},
                {"_id": 0}
            )

            if expediente:
                print("\nExpediente encontrado:")
                print(expediente)
            else:
                print("\nNo existe el expediente")
        else:
            print("\nNo existe acceso vigente")

            r.set(
                clave,
                "permitido",
                ex=7200,
                nx=True
            )

            print("Acceso temporal otorgado por 2 horas")

    elif opcion == "4":
        print("\n[OP-4] Detección de conflicto de interés")

        expediente_id = input("Expediente a evaluar: ")

        with neo4j_driver.session() as session:
            resultado = session.run("""
                MATCH (e:Expediente {expediente_id: $expediente_id})-[:CONEXO_A*1..3]->(conexo:Expediente)
                RETURN conexo.expediente_id AS expediente_conexo
                LIMIT 5
            """, expediente_id=expediente_id)

            conexos = [record["expediente_conexo"] for record in resultado]

        if conexos:
            print("\nPosible conflicto detectado")
            print("Expedientes conexos encontrados:")
            for c in conexos:
                print("-", c)

            db.actuaciones.insert_one({
                "actuacion_id": f"ALERTA_{expediente_id}",
                "expediente_id": expediente_id,
                "tipo": "alerta_conflicto",
                "autor": "sistema",
                "texto": f"Se detectaron causas conexas: {conexos}"
            })

            print("\nAlerta registrada en MongoDB")
        else:
            print("\nNo se detectaron causas conexas")

    elif opcion == "5":
        print("\n[OP-5] Cierre de audiencia")

        expediente_id = input("Expediente: ")
        sala = input("Sala: ")

        r.hset(
            f"sala:{sala}",
            mapping={
                "estado": "en_preparacion",
                "expediente_activo": "",
                "hora_fin_estimada": ""
            }
        )

        r.xadd(
            "notificaciones",
            {
                "evento": "fin_audiencia",
                "expediente": expediente_id,
                "sala": sala
            }
        )

        db.actuaciones.insert_one({
            "actuacion_id": f"CIERRE_AUDIENCIA_{expediente_id}",
            "expediente_id": expediente_id,
            "tipo": "fin_audiencia",
            "autor": "sistema",
            "texto": f"Se cerró la audiencia del expediente {expediente_id} en la sala {sala}. Acta persistida correctamente."
        })

        expediente_conexo = "EXP50"

        with neo4j_driver.session() as session:
            session.run("""
                MATCH (e1:Expediente {expediente_id: $expediente_id})
                MATCH (e2:Expediente {expediente_id: $expediente_conexo})
                MERGE (e1)-[:CONEXO_A {tipo: "resolucion_audiencia"}]->(e2)
            """,
            expediente_id=expediente_id,
            expediente_conexo=expediente_conexo)

        print("\nAudiencia cerrada correctamente")
        print(f"Sala {sala} marcada como en_preparacion")
        print("Notificación de cierre enviada a Redis")
        print("Acta registrada en MongoDB")
        print(f"Relación CONEXO_A agregada en Neo4j entre {expediente_id} y {expediente_conexo}")

    elif opcion == "0":
        print("\nSaliendo...")
        break

    else:
        print("\nOpción inválida")