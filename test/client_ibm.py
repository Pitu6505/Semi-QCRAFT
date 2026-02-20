# cliente_ibm.py
import requests
import time
import json

URL_SERVIDOR = "http://127.0.0.1:8000"

print("=== CLIENTE QCaaS: ENVIANDO TRABAJOS MULTIPLES A IBM ===")

datos_peticion = {
    "urls": {
        "UsuarioIBM_CircuitoA": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/mapping/20QBT_4CYC_8GN_1.0P2_0_vq.py",
        "UsuarioIBM_CircuitoB": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/Deutsch-Jozsa_qcraft.py"
    },
    "provider": "IBM",
    "backend_name": "ibm_fez"
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

print("\n⏳ Esperando la cola de IBM Quantum...")
while True:
    res_resultados = requests.get(f"{URL_SERVIDOR}/results/{job_id}")
    datos_resultados = res_resultados.json()
    
    estado = datos_resultados["status"]
    
    if estado == "DONE":
        print("\n🎉 ¡EJECUCIÓN COMPLETADA!")
        print("📊 Resultados matemáticos separados de forma privada:")
        print(json.dumps(datos_resultados["resultados_por_usuario"], indent=4))
        break
    elif estado in ["ERROR", "CANCELLED"]:
        print(f"\n❌ El trabajo falló en IBM. Estado: {estado}")
        break
    else:
        print(f"   -> Cola de IBM: {estado}. Re-consultando en 10 segundos...")
        time.sleep(10)