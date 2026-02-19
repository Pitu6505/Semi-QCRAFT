# main.py
from qiskit import QuantumCircuit
from Ibm_api import get_backend_data
from circuit_Compresor import AdvancedTopologyCompressor

# Importamos las credenciales de forma segura
from config import IBM_API_KEY, IBM_INSTANCE_CRN

# Usamos las variables importadas
cmap, qubit_props, gate_props, backend = get_backend_data(
    IBM_API_KEY, 
    IBM_INSTANCE_CRN, 
    "ibm_fez"
)

if cmap is not None:
    compressor = AdvancedTopologyCompressor(coupling_map=cmap)

    qc = QuantumCircuit(4, 4)
    qc.h(0)
    qc.cx(0, 1)
    qc.barrier() 
    qc.x(2)
    qc.cx(2, 3)
    qc.measure([0, 1, 2, 3], [0, 1, 2, 3])

    print("\n--- INICIANDO OPTIMIZACIÓN ---")
    print("Circuito Original:")
    print(qc)
    circuito_optimizado = compressor.compress_and_map(qc)
    
    print("\n--- CIRCUITO OPTIMIZADO ---")
    print(circuito_optimizado)
    
    # 3. AQUÍ ENTRARÍA TU MOCHILA
    # Le pasas: 
    # - circuito_optimizado (que ahora es más pequeño)
    # - qubit_props (para que tu mochila elija las mejores zonas del chip basándose en la calibración)