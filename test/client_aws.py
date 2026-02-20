# cliente_aws.py
import requests
import time
import json

URL_SERVIDOR = "http://127.0.0.1:8000"

print("=== CLIENTE QCaaS: ENVIANDO TRABAJOS MÚLTIPLES A AWS ===")

# 1. El usuario envía DOS circuitos para forzar a usar la Mochila
datos_peticion = {
    "urls": {
        "UsuarioAWS_CircuitoA": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/mapping/20QBT_4CYC_8GN_1.0P2_0_vq.py",
        "UsuarioAWS_CircuitoB": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/Deutsch-Jozsa_qcraft.py"
    },
    "provider": "AWS",
    "backend_name": "Ankaa-3"
}

print(f"📦 Enviando bloque de circuitos al servidor...")
respuesta = requests.post(f"{URL_SERVIDOR}/submit_jobs", json=datos_peticion)

if respuesta.status_code != 200:
    print(f"❌ Error del servidor: {respuesta.text}")
    exit()

info_trabajo = respuesta.json()
job_id = info_trabajo["job_id"]
print(f"✅ ¡Aceptado por la mochila! Job ID: {job_id}")
print(f"☁️  Enrutado a: {info_trabajo['provider']} ({info_trabajo['backend']})")
print(f"👥 Usuarios empaquetados juntos: {info_trabajo['usuarios_aceptados']}")

print("\n⏳ Esperando la cola de AWS Braket...")
while True:
    res_resultados = requests.get(f"{URL_SERVIDOR}/results/{job_id}")
    
    # Si hay un error de red temporal, esperamos y reintentamos
    if res_resultados.status_code != 200:
        print(f"   -> Servidor no listo (HTTP {res_resultados.status_code}). Reintentando...")
        time.sleep(5)
        continue
        
    datos_resultados = res_resultados.json()
    estado = str(datos_resultados.get("status", "")).upper()
    
    # Flexibilidad total para IBM y AWS
    if "DONE" in estado or "COMPLETED" in estado:
        print("\n🎉 ¡EJECUCIÓN COMPLETADA EN AWS!")
        print("📊 Resultados matemáticos separados de forma privada:")
        print(json.dumps(datos_resultados.get("resultados_por_usuario", {}), indent=4))
        break
    elif "ERROR" in estado or "CANCELLED" in estado or "FAILED" in estado:
        print(f"\n❌ El trabajo falló en la nube. Estado: {estado}")
        break
    else:
        print(f"   -> Cola de hardware: {estado}. Re-consultando en 10 segundos...")
        time.sleep(10)