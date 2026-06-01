from pymongo import MongoClient
import redis
from neo4j import GraphDatabase
import time
from collections import defaultdict

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["sistema_judicial"]

r = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

neo4j_driver = GraphDatabase.driver(
    "neo4j://127.0.0.1:7687",
    auth=("neo4j", "Datos2026")
)

AGENDA_KEY = "agenda:Juzgado1:20260601"

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
    print("6 - Marcar sala como disponible")
    print("7 - Registrar audiencia en agenda")
    print("8 - Revocar acceso temporal")
    print("0 - Salir")

    opcion = input("\nOpción: ")

    if opcion == "1":
        print("\n[OP-1] Panel operativo del juzgado")

        print("\n=== SALAS ===")
        salas_disponibles = []

        for sala in range(1, 4):
            datos = r.hgetall(f"sala:{sala}")
            if datos:
                estado = datos.get("estado", "-")
                print(f"Sala {sala} | Estado: {estado}")

                if estado == "disponible":
                    salas_disponibles.append(sala)

        print("\n=== SALAS DISPONIBLES ===")
        if salas_disponibles:
            for sala in salas_disponibles:
                print(f"Sala {sala} disponible")
        else:
            print("No hay salas disponibles")

        print("\n=== AGENDA DEL DÍA ===")
        agenda = r.zrange(AGENDA_KEY, 0, -1, withscores=True)

        if agenda:
            for expediente, horario in agenda:
                print(f"{expediente} -> {int(horario)}")
        else:
            print("Sin audiencias pendientes")

        print("\n=== PRÓXIMA AUDIENCIA ===")
        proxima = r.zrange(AGENDA_KEY, 0, 0, withscores=True)

        if proxima:
            expediente, horario = proxima[0]
            print(f"Próxima audiencia: {expediente} -> {int(horario)}")
        else:
            print("No hay próxima audiencia")

        print("\n=== AUDIENCIAS DE LAS PRÓXIMAS 2 HORAS ===")
        if proxima:
            base = int(proxima[0][1])
            limite = base + 7200

            proximas = r.zrangebyscore(
                AGENDA_KEY,
                base,
                limite,
                withscores=True
            )

            for expediente, horario in proximas:
                print(f"{expediente} -> {int(horario)}")
        else:
            print("No hay audiencias para listar")

        print("\n=== SOLAPAMIENTOS ===")
        horarios = defaultdict(list)

        for expediente, horario in agenda:
            horarios[int(horario)].append(expediente)

        hay_solapamiento = False

        for horario, expedientes in horarios.items():
            if len(expedientes) > 1:
                hay_solapamiento = True
                print(f"Horario {horario}: {expedientes}")

        if not hay_solapamiento:
            print("No se detectaron solapamientos")

        print("\n=== CARGA DEL DÍA ===")
        print(f"Total de audiencias programadas: {r.zcard(AGENDA_KEY)}")

        print("\n=== AUDIENCIAS CON RETRASO ===")
        ahora = int(time.time())
        hay_retraso = False

        for sala in range(1, 4):
            datos = r.hgetall(f"sala:{sala}")

            if datos.get("estado") == "en_audiencia":
                fin_estimado = datos.get("hora_fin_estimada_ts")

                if fin_estimado and ahora > int(fin_estimado) + 1800:
                    hay_retraso = True
                    print(f"Sala {sala} con audiencia retrasada")

        if not hay_retraso:
            print("No se detectaron audiencias con retraso")

        print("\n=== ÚLTIMAS NOTIFICACIONES ===")
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

        hora_fin_estimada_ts = int(time.time()) + 3600

        r.hset(
            f"sala:{sala}",
            mapping={
                "estado": "en_audiencia",
                "expediente_activo": expediente_id,
                "hora_fin_estimada": "18:00",
                "hora_fin_estimada_ts": hora_fin_estimada_ts
            }
        )

        r.zrem(AGENDA_KEY, expediente_id)

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
                "hora_fin_estimada": "",
                "hora_fin_estimada_ts": ""
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

    elif opcion == "6":
        print("\n[Redis] Marcar sala como disponible")

        sala = input("Sala: ")

        r.hset(
            f"sala:{sala}",
            mapping={
                "estado": "disponible",
                "expediente_activo": "",
                "hora_fin_estimada": "",
                "hora_fin_estimada_ts": ""
            }
        )

        print(f"Sala {sala} marcada como disponible")

    elif opcion == "7":
        print("\n[Redis] Registrar audiencia en agenda")

        expediente_id = input("Expediente: ")
        timestamp = int(input("Timestamp de inicio: "))

        r.zadd(AGENDA_KEY, {expediente_id: timestamp})

        print(f"Audiencia {expediente_id} registrada en agenda")

    elif opcion == "8":
        print("\n[Redis] Revocar acceso temporal")

        expediente_id = input("Expediente: ")
        operador_id = input("Operador: ")

        clave = f"acceso:{expediente_id}:{operador_id}"

        eliminado = r.delete(clave)

        if eliminado:
            print("Acceso revocado correctamente")
        else:
            print("No existía acceso vigente para revocar")

    elif opcion == "0":
        print("\nSaliendo...")
        break

    else:
        print("\nOpción inválida")