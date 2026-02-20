import requests
from qiskit import QuantumCircuit, transpile
from circuit_Compresor import AdvancedTopologyCompressor

# =======================================================
# 1. TUS URLs DE GITHUB (Entrada del QCaaS)
# =======================================================
urls_usuarios = {
    "Combinacional-Mapping-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/mapping/20QBT_16CYC_32GN_1.0P2_0_vq.py",
    "Combinacional-Mapping-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/mapping/20QBT_4CYC_8GN_1.0P2_0_vq.py",
    "Popular-dj-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/Deutsch-Jozsa_qcraft.py"
}

# =======================================================
# 2. FUNCIONES DEL ORQUESTADOR
# =======================================================
def descargar_circuito(url):
    """Descarga el código, lo limpia de librerías obsoletas, arregla bugs del usuario y extrae el QuantumCircuit"""
    nombre_archivo = url.split('/')[-1]
    print(f"\n   [GET] Descargando: {nombre_archivo}...")
    
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"   ❌ Error HTTP {resp.status_code} al descargar.")
        return None
    
    # --- AUTO-SANITIZADOR DE CÓDIGO 2.0 (Magia para QCaaS) ---
    codigo_original = resp.text
    lineas_limpias = []
    
    # Lista ampliada de palabras que no queremos ejecutar
    palabras_prohibidas = [
        "qiskit_ibm", "Aer", "execute", "backend =", "job =", 
        "job_result", "IBMProvider", "provider", "shots", "qc_basis"
    ]
    
    for linea in codigo_original.split('\n'):
        # 1. Filtramos todo lo relacionado con ejecuciones antiguas
        if any(palabra in linea for palabra in palabras_prohibidas):
            continue
            
        # 2. Arreglamos el bug de Qcraft: Inyectar el registro clásico si el usuario lo olvidó
        if "circuit = QuantumCircuit(qreg_q)" in linea and "creg_c" not in linea:
            linea = linea.replace("circuit = QuantumCircuit(qreg_q)", "circuit = QuantumCircuit(qreg_q, creg_c)")
            
        lineas_limpias.append(linea)
        
    codigo_limpio = '\n'.join(lineas_limpias)
    # ---------------------------------------------------------

    memoria = {}
    try:
        # Ejecutamos el código ya limpio y parcheado
        exec(codigo_limpio, globals(), memoria)
        
        for var, val in memoria.items():
            if isinstance(val, QuantumCircuit):
                print(f"   ✅ Circuito extraído: {val.num_qubits} qubits lógicos.")
                return val
                
        print("   ❌ El archivo no contenía ningún objeto QuantumCircuit válido.")
        return None
        
    except Exception as e:
        print(f"   ❌ Error interno al leer el circuito del usuario: {e}")
        return None

def mochila_simple(circuitos_info, capacidad_maquina):
    """
    Algoritmo Greedy: Ordena de menor a mayor tamaño comprimido 
    y mete los que quepan hasta llenar la máquina.
    """
    print(f"\n🎒 Abriendo mochila (Capacidad: {capacidad_maquina} qubits físicos)...")
    
    # Ordenamos por tamaño comprimido (el índice 2 de nuestra tupla)
    circuitos_info.sort(key=lambda x: x[2]) 
    
    ganadores = []
    espacio_ocupado = 0
    
    for nombre, circ, tamaño_comp in circuitos_info:
        if espacio_ocupado + tamaño_comp <= capacidad_maquina:
            ganadores.append((nombre, circ))
            espacio_ocupado += tamaño_comp
            print(f"  ✅ ACEPTADO: {nombre} (Ocupa {tamaño_comp}q) | Espacio restante: {capacidad_maquina - espacio_ocupado}q")
        else:
            print(f"  ❌ RECHAZADO: {nombre} (Ocupa {tamaño_comp}q) | No hay espacio suficiente.")
            
    return ganadores

def ensamblar_mega_circuito(ganadores):
    """Cose los circuitos ganadores en uno solo grande"""
    total_q = sum(circ.num_qubits for _, circ in ganadores)
    total_c = sum(circ.num_clbits for _, circ in ganadores)
    
    mega_circuito = QuantumCircuit(total_q, total_c)
    
    offset_q = 0
    offset_c = 0
    for nombre, circ in ganadores:
        # Añadimos las instrucciones desplazando los cables para que no se pisen
        mega_circuito.compose(
            circ, 
            qubits=range(offset_q, offset_q + circ.num_qubits),
            clbits=range(offset_c, offset_c + circ.num_clbits),
            inplace=True
        )
        offset_q += circ.num_qubits
        offset_c += circ.num_clbits
        
    return mega_circuito

# =======================================================
# 3. EJECUCIÓN DEL FLUJO PRINCIPAL
# =======================================================
print("=== INICIANDO PLATAFORMA QCaaS ===")
compresor_estimador = AdvancedTopologyCompressor()

cola_trabajos = []

# PASO A: Descargar y evaluar
print("\n📥 Descargando y evaluando trabajos de los usuarios...")
for nombre, url in urls_usuarios.items():
    circ_original = descargar_circuito(url)
    if circ_original:
        
        # MOSTRAR CIRCUITO ORIGINAL
        print(f"\n--- CIRCUITO ORIGINAL: {nombre} ({circ_original.num_qubits}q) ---")
        print(circ_original.draw(fold=-1)) 
        
        # 1. Limpieza Lógica
        circ_limpio = transpile(circ_original, optimization_level=3)
        # 2. Estimación
        circ_estimado = compresor_estimador.compress_and_map(circ_limpio)
        tamaño_comprimido = circ_estimado.num_qubits

        print("\n Circuito Optimizado")
        print(circ_estimado.draw(fold=-1))
        
        cola_trabajos.append((nombre, circ_limpio, tamaño_comprimido))
        print(f"   -> Resumen {nombre}: Lógico={circ_limpio.num_qubits}q | Comprimido estimado={tamaño_comprimido}q")

# PASO B: La Mochila
CAPACIDAD_QPU = 25 
trabajos_ganadores = mochila_simple(cola_trabajos, CAPACIDAD_QPU)

# PASO C: Ensamblar e inyectar al hardware
if trabajos_ganadores:
    print("\n🧩 Ensamblando trabajos ganadores en un solo Mega-Circuito...")
    mega_circuito = ensamblar_mega_circuito(trabajos_ganadores)
    print(f"   -> Tamaño Lógico Total del paquete: {mega_circuito.num_qubits} qubits.")
    
    print("\n⚙️  Pasando el Mega-Circuito por el Compresor Dinámico Final...")
    compresor_final = AdvancedTopologyCompressor() 
    paquete_listo_para_enviar = compresor_final.compress_and_map(mega_circuito)
    
    print("\n🚀 ¡PAQUETE QCaaS FINAL LISTO PARA ENVIAR A LA NUBE!")
    print(f"   -> Qubits Físicos Finales: {paquete_listo_para_enviar.num_qubits}")
    
    # MOSTRAR EL MEGA-CIRCUITO COMPRIMIDO FINAL
    print("\n=== MEGA-CIRCUITO FINAL COMPRIMIDO ===")
    print(paquete_listo_para_enviar.draw(fold=-1))