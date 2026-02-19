from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from circuit_Compresor import AdvancedTopologyCompressor

# =======================================================
# 1. DEFINICIÓN DEL CIRCUITO SIMON (Qiskit 1.0+)
# =======================================================
qreg_q = QuantumRegister(6, 'q')
creg_c = ClassicalRegister(6, 'c')
circuit = QuantumCircuit(qreg_q, creg_c)

# Primera parte: Superposición
circuit.h(qreg_q[0])
circuit.h(qreg_q[1])
circuit.h(qreg_q[2])

circuit.barrier(qreg_q[0], qreg_q[1], qreg_q[2], qreg_q[3], qreg_q[4], qreg_q[5])

# Segunda parte: Oráculo de Simon
circuit.cx(qreg_q[0], qreg_q[3])
circuit.cx(qreg_q[1], qreg_q[4])
circuit.cx(qreg_q[2], qreg_q[5])
circuit.cx(qreg_q[1], qreg_q[4]) # Nota: ¡Esta puerta anula a la anterior lógicamente!
circuit.cx(qreg_q[1], qreg_q[5])

circuit.barrier(qreg_q[0], qreg_q[1], qreg_q[2], qreg_q[3], qreg_q[4], qreg_q[5])

# Tercera parte: Interferencia
circuit.h(qreg_q[0])
circuit.h(qreg_q[1])
circuit.h(qreg_q[2])

# Mediciones finales (todas juntas al final, como suele hacer el usuario)
circuit.measure(qreg_q[0], creg_c[0])
circuit.measure(qreg_q[1], creg_c[1])
circuit.measure(qreg_q[2], creg_c[2])
circuit.measure(qreg_q[3], creg_c[3])
circuit.measure(qreg_q[4], creg_c[4])
circuit.measure(qreg_q[5], creg_c[5])

print("=== CIRCUITO ORIGINAL ===")
print(f"Qubits lógicos: {circuit.num_qubits}")
print("\nCircuito original enviado por el usuario:")
print(circuit)

# =======================================================
# 2. PIPELINE DE OPTIMIZACIÓN (Tu Arquitectura QCaaS)
# =======================================================

# FASE 1: Limpieza Lógica (Software)
# Esto eliminará el doble CX(1,4) que hay en el oráculo antes de comprimir
print("\n--- FASE 1: Limpieza Lógica (Qiskit Nivel 3) ---")
circuito_limpio = transpile(circuit, optimization_level=3)

# FASE 2: Compresión Dinámica (Hardware-Agnostic)
# Instanciamos el compresor (sin topología física para ver la compresión pura)
compressor = AdvancedTopologyCompressor()

print("\n--- FASE 2: Compresión Dinámica (Adelanto de medidas + Reset) ---")
circuito_final_optimizado = compressor.compress_and_map(circuito_limpio)

print("\n=== CIRCUITO FINAL OPTIMIZADO ===")
print(circuito_final_optimizado)