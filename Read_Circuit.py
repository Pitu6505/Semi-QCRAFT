import requests
from qiskit import QuantumCircuit

# El diccionario que me pasaste
urls = {
    # "Combinational-Mapping-1": "...",
    "Popular-dj-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/Deutsch-Jozsa_qcraft.py"
}

def descargar_y_extraer_circuito(url):
    """Descarga un archivo .py de Qiskit desde una URL y extrae el objeto QuantumCircuit"""
    print(f"📥 Descargando circuito desde: {url.split('/')[-1]}...")
    
    # 1. Hacemos la petición a GitHub
    response = requests.get(url)
    if response.status_code != 200:
        print("❌ Error al descargar el archivo.")
        return None
    
    codigo_python = response.text
    
    # 2. Creamos un espacio de memoria aislado (diccionario)
    espacio_de_memoria = {}
    
    try:
        # 3. Ejecutamos el código Python descargado dinámicamente
        # Esto construirá las variables (como 'circuit', 'qreg_q', etc.)
        exec(codigo_python, globals(), espacio_de_memoria)
        
        # 4. Buscamos el objeto QuantumCircuit en la memoria
        for nombre_variable, valor in espacio_de_memoria.items():
            if isinstance(valor, QuantumCircuit):
                print(f"✅ Circuito extraído con éxito: {valor.num_qubits} qubits.")
                return valor
                
        print("❌ No se encontró ningún objeto QuantumCircuit en el código.")
        return None
        
    except Exception as e:
        print(f"❌ Error al ejecutar el código del circuito: {e}")
        return None

# Prueba del flujo
for nombre_tarea, url in urls.items():
    print(f"\n--- Procesando Tarea: {nombre_tarea} ---")
    
    # 1. Obtener el circuito original
    circuito_original = descargar_y_extraer_circuito(url)
    
    if circuito_original:
        # 2. AQUÍ ENTRARÍA TU COMPRESOR
        # circuito_limpio = transpile(circuito_original, optimization_level=3)
        # circuito_comprimido = compressor.compress_and_map(circuito_limpio)
        # 
        # 3. Y LUEGO A LA MOCHILA...
        pass