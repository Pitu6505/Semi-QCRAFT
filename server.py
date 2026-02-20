from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import requests

from qiskit import QuantumCircuit, transpile
from circuit_Compresor import AdvancedTopologyCompressor

# --- IMPORTAMOS TUS MÓDULOS LOCALES ---
from config import IBM_API_KEY, IBM_INSTANCE_CRN
from Ibm_api import get_backend_data as get_ibm_data
from Aws_api import get_aws_backend_data

app = FastAPI(title="QCaaS Orchestrator", description="Plataforma Multi-Cloud de Multiplexación Cuántica")

# Diccionario en memoria para guardar el estado y los objetos de los trabajos
base_de_datos_trabajos = {}

# --- MODELOS DE DATOS ---
class JobRequest(BaseModel):
    urls: Dict[str, str]
    provider: str = "IBM"  # Permite elegir "IBM" o "AWS"
    backend_name: Optional[str] = None # Para forzar una máquina en concreto (ej. "ibm_fez" o "Ankaa-3")

# --- FUNCIONES AUXILIARES ---
def descargar_circuito(url: str):
    print(f"   [GET] Descargando desde GitHub: {url.split('/')[-1]}")
    resp = requests.get(url)
    if resp.status_code != 200: return None
    
    lineas_limpias = []
    palabras_prohibidas = ["qiskit_ibm", "Aer", "execute", "backend =", "job =", "job_result", "IBMProvider", "provider", "shots", "qc_basis"]
    
    for linea in resp.text.split('\n'):
        if any(p in linea for p in palabras_prohibidas): continue
        if "circuit = QuantumCircuit(qreg_q)" in linea and "creg_c" not in linea:
            linea = linea.replace("circuit = QuantumCircuit(qreg_q)", "circuit = QuantumCircuit(qreg_q, creg_c)")
        lineas_limpias.append(linea)
        
    memoria = {}
    try:
        exec('\n'.join(lineas_limpias), globals(), memoria)
        for val in memoria.values():
            if isinstance(val, QuantumCircuit): return val
    except: pass
    return None

def mochila_simple(circuitos_info, capacidad):
    circuitos_info.sort(key=lambda x: x[2]) 
    ganadores, ocupado = [], 0
    for nombre, circ, tamaño in circuitos_info:
        if ocupado + tamaño <= capacidad:
            ganadores.append((nombre, circ))
            ocupado += tamaño
    return ganadores

# --- ENDPOINTS DEL SERVIDOR ---

@app.post("/submit_jobs")
async def submit_jobs(request: JobRequest):
    print(f"\n[API] Petición recibida para el proveedor: {request.provider}")
    
    # 1. CONECTAR AL HARDWARE ELEGIDO
    if request.provider.upper() == "IBM":
        b_name = request.backend_name or "ibm_fez"
        cmap, _, _, backend = get_ibm_data(IBM_API_KEY, IBM_INSTANCE_CRN, b_name)
    elif request.provider.upper() == "AWS":
        b_name = request.backend_name or "Ankaa-3"
        cmap, backend = get_aws_backend_data(b_name)
    else:
        raise HTTPException(status_code=400, detail="Proveedor no soportado. Elige 'IBM' o 'AWS'.")

    if backend is None:
        raise HTTPException(status_code=503, detail="No se pudo conectar a la máquina cuántica.")

    capacidad_maquina = backend.num_qubits

    # 2. DESCARGAR Y ESTIMAR COMPRESIÓN
    compresor_estimador = AdvancedTopologyCompressor()
    cola_trabajos = []
    
    for nombre, url in request.urls.items():
        circ = descargar_circuito(url)
        if circ:
            circ_limpio = transpile(circ, optimization_level=3)
            tamaño_comp = compresor_estimador.compress_and_map(circ_limpio).num_qubits
            cola_trabajos.append((nombre, circ_limpio, tamaño_comp))
            
    if not cola_trabajos:
        raise HTTPException(status_code=400, detail="No se pudo extraer ningún circuito válido de las URLs.")

    # 3. MOCHILA MULTIPLEXADORA
    ganadores = mochila_simple(cola_trabajos, capacidad_maquina)
    if not ganadores:
         raise HTTPException(status_code=400, detail="Los circuitos son demasiado grandes para la máquina elegida.")

    # 4. ENSAMBLAJE Y MAPEO DE BITS CLÁSICOS (CORREGIDO)
    # Primero calculamos el tamaño total que necesitamos
    total_q = sum(circ.num_qubits for _, circ in ganadores)
    total_c = sum(circ.num_clbits for _, circ in ganadores)
    
    # Creamos un Mega-Circuito pre-asignado (evita colisiones de nombres de registros)
    mega_circuito = QuantumCircuit(total_q, total_c)
    mapa_bits = {} 
    offset_q = 0
    offset_c = 0
    
    for nombre, circ in ganadores:
        # Añadimos las instrucciones desplazando los cables lógicos para que no se pisen
        mega_circuito.compose(circ, 
                              qubits=range(offset_q, offset_q + circ.num_qubits), 
                              clbits=range(offset_c, offset_c + circ.num_clbits), 
                              inplace=True)
        
        # Guardamos que el "Usuario X" lee desde el bit Y hasta el Z
        mapa_bits[nombre] = {"inicio": offset_c, "longitud": circ.num_clbits}
        
        # Avanzamos los desplazamientos para el siguiente usuario
        offset_q += circ.num_qubits
        offset_c += circ.num_clbits

    # 5. COMPRESIÓN FÍSICA Y ENVÍO A LA NUBE
    print(f"\n[API] Compresión final adaptada a {backend.name}...")
    compresor_final = AdvancedTopologyCompressor(coupling_map=cmap)
    mega_comprimido = compresor_final.compress_and_map(mega_circuito)
    
    # IMPORTANTE: Nivel 0 para que la nube no destruya nuestra compresión
    mega_transpilado = transpile(mega_comprimido, backend=backend, optimization_level=0) 
    
    print(f"[API] Enviando paquete de {mega_transpilado.num_qubits} qubits físicos a {request.provider}...")
    job = backend.run(mega_transpilado, shots=1024)
    job_id = job.job_id()
    
    # Guardamos el objeto 'job' entero para poder preguntarle el estado luego
    base_de_datos_trabajos[job_id] = {
        "job_obj": job,
        "provider": request.provider,
        "backend_name": backend.name,
        "mapa_bits": mapa_bits
    }
    
    return {
        "message": "Mega-Circuito empaquetado y enviado con éxito",
        "job_id": job_id,
        "provider": request.provider,
        "backend": backend.name,
        "usuarios_aceptados": list(mapa_bits.keys())
    }

@app.get("/results/{job_id:path}")
async def get_results(job_id: str):
    if job_id not in base_de_datos_trabajos:
        raise HTTPException(status_code=404, detail="Job ID no encontrado en la plataforma")
        
    job_info = base_de_datos_trabajos[job_id]
    job = job_info["job_obj"]
    
# Extraemos el estado y lo ponemos en mayúsculas para evitar fallos
    status = job.status().name if hasattr(job.status(), 'name') else str(job.status())
    status = status.upper()
    
    # Aceptamos tanto el DONE de IBM como el COMPLETED de AWS
    if "DONE" not in status and "COMPLETED" not in status:
        return {"job_id": job_id, "status": status, "message": "Ejecutándose en el refrigerador cuántico..."}
        
    # --- DESEMPAQUETADO DE RESULTADOS (EL CORTE DEL TETRIS) ---
    conteos_crudos = job.result().get_counts()
    resultados_separados = {nombre: {} for nombre in job_info["mapa_bits"]}
    
    for bitstring_gigante, cantidad in conteos_crudos.items():
        bits_invertidos = bitstring_gigante.replace(" ", "")[::-1]
        
        for nombre, mapa in job_info["mapa_bits"].items():
            inicio = mapa["inicio"]
            longitud = mapa["longitud"]
            
            trozo_usuario = bits_invertidos[inicio:inicio+longitud][::-1]
            
            if trozo_usuario in resultados_separados[nombre]:
                resultados_separados[nombre][trozo_usuario] += cantidad
            else:
                resultados_separados[nombre][trozo_usuario] = cantidad

    return {
        "job_id": job_id,
        "status": status,
        "resultados_por_usuario": resultados_separados
    }