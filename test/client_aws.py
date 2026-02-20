# cliente_aws.py
import requests
import time
import json

# La dirección donde está corriendo tu orquestador FastAPI local
URL_SERVIDOR = "http://127.0.0.1:8000"

print("=== CLIENTE QCaaS: ENVIANDO TRABAJO A AWS ===")

# 1. Preparamos el paquete de datos (Payload)
datos_peticion = {
    "urls": {
        "UsuarioAWS_DeutschJozsa": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/Deutsch-Jozsa_qcraft.py"
    },
    "provider": "AWS",
    "backend_name": "Ankaa-3"
}

# 2. Enviamos los circuitos a la mochila del servidor
print(f"📦 Enviando circuitos al servidor...")
respuesta = requests.post(f"{URL_SERVIDOR}/submit_jobs", json=datos_peticion)

if respuesta.status_code != 200:
    print(f"❌ Error del servidor: {respuesta.text}")
    exit()

info_trabajo = respuesta.json()
job_id = info_trabajo["job_id"]
print(f"✅ ¡Aceptado por el orquestador! Job ID: {job_id}")
print(f"☁️  Enrutado a: {info_trabajo['provider']} ({info_trabajo['backend']})")

# 3. Nos quedamos esperando los resultados (Polling)
print("\n⏳ Esperando a que el hardware cuántico termine la ejecución...")
while True:
    res_resultados = requests.get(f"{URL_SERVIDOR}/results/{job_id}")
    datos_resultados = res_resultados.json()
    
    estado = datos_resultados["status"]
    
    if estado == "DONE":
        print("\n🎉 ¡EJECUCIÓN COMPLETADA!")
        print("📊 Resultados extraídos y desempaquetados:")
        print(json.dumps(datos_resultados["resultados_por_usuario"], indent=4))
        break
    elif estado in ["ERROR", "CANCELLED"]:
        print(f"\n❌ El trabajo falló en la nube. Estado: {estado}")
        break
    else:
        print(f"   -> Estado actual: {estado}. Volviendo a comprobar en 10 segundos...")
        time.sleep(10)