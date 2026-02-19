# main.py
from qiskit import QuantumCircuit, transpile
from Ibm_api import get_backend_data
from circuit_Compresor import AdvancedTopologyCompressor
from config import IBM_API_KEY, IBM_INSTANCE_CRN

# 1. Obtenemos los datos de la máquina real
cmap, qubit_props, gate_props, backend = get_backend_data(
    IBM_API_KEY, 
    IBM_INSTANCE_CRN, 
    "ibm_fez"
)

# Simulamos que el usuario nos envía el circuito "sucio" (ej. shor_qcraft)
# que tiene operaciones redundantes o mal ordenadas.
circuito_usuario = QuantumCircuit(4, 4)

# Tarea 1: Ocurre al principio
circuito_usuario.cx(1, 2)
circuito_usuario.barrier() 
circuito_usuario.cx(0, 3) 
circuito_usuario.measure([0, 1, 2, 3], [0, 1, 2, 3])

print("\n=== INICIANDO PIPELINE QCaaS ===")

if cmap is not None:

    print("\n Circuito original enviado por el usuario:")
    print(circuito_usuario)
    # =======================================================
    # PASO 1: LIMPIEZA LÓGICA (Pre-procesamiento Software)
    # =======================================================
    print("1. Ejecutando limpieza lógica (Qiskit Nivel 3)...")
    circuito_limpio = transpile(circuito_usuario, optimization_level=3)
    
    # =======================================================
    # PASO 2 y 3: COMPRESIÓN DINÁMICA Y ENRUTAMIENTO FÍSICO
    # =======================================================
    print("\n2. Ejecutando Compresión Temporal y Mapeo Físico...")
    compressor = AdvancedTopologyCompressor(coupling_map=cmap)
    
    circuito_final_optimizado = compressor.compress_and_map(circuito_limpio)
    
    print("\n=== OPTIMIZACIÓN COMPLETADA ===")
    print(circuito_final_optimizado)
    
