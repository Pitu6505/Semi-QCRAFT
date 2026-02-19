from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

class DynamicCompressor:
    """
    Clase para comprimir circuitos cuánticos utilizando Qubit Reuse (Reset).
    """
    def __init__(self):
        pass

    def get_qubit_lifetimes(self, circuit):
        """
        Calcula el intervalo de vida de cada qubit simulando un reloj interno.
        """
        qubit_lifetimes = {q: {'start': float('inf'), 'end': -1} for q in circuit.qubits}
        qubit_current_time = {q: 0 for q in circuit.qubits}
        
        for inst in circuit.data:
            op = inst.operation
            qargs = inst.qubits
            
            if not qargs:
                continue
                
            # El tiempo de inicio de esta puerta es cuando el qubit más "atrasado" esté libre
            start_time = max(qubit_current_time[q] for q in qargs)
            
            # La barrera es solo para sincronizar el reloj lógico, no ocupa hardware físicamente
            if op.name == 'barrier':
                for q in qargs:
                    qubit_current_time[q] = start_time
                continue
                
            end_time = start_time + 1 # Asumimos duración de 1 paso por puerta
            
            # Actualizamos el registro de vida del qubit
            for q in qargs:
                if qubit_lifetimes[q]['start'] == float('inf'):
                    qubit_lifetimes[q]['start'] = start_time
                qubit_lifetimes[q]['end'] = end_time
                qubit_current_time[q] = end_time
                
        return qubit_lifetimes

    def compress(self, circuit):
        lifetimes = self.get_qubit_lifetimes(circuit)
        
        # Ordenamos los qubits por el momento en que empiezan a usarse
        sorted_qubits = sorted(lifetimes.keys(), key=lambda q: lifetimes[q]['start'])
        
        physical_lanes_end_time = []
        logical_to_physical_map = {}
        resets_needed = {}

        for logical_q in sorted_qubits:
            start = lifetimes[logical_q]['start']
            end = lifetimes[logical_q]['end']
            
            # Si el qubit no se usa nunca, lo saltamos
            if start == float('inf'):
                continue
                
            assigned = False
            
            for lane_idx, lane_end_time in enumerate(physical_lanes_end_time):
                # CAMBIO CLAVE (<=): Si un carril termina en t=3, otro puede empezar en t=3
                if lane_end_time <= start:
                    physical_lanes_end_time[lane_idx] = end
                    logical_to_physical_map[logical_q] = lane_idx
                    resets_needed[logical_q] = True # Se reutiliza, requiere reset
                    assigned = True
                    break
            
            if not assigned:
                physical_lanes_end_time.append(end)
                new_lane_idx = len(physical_lanes_end_time) - 1
                logical_to_physical_map[logical_q] = new_lane_idx
                resets_needed[logical_q] = False # Es el primero del carril, no requiere reset

        num_physical_qubits = len(physical_lanes_end_time)
        print(f"✨ Compresión completada: {len(circuit.qubits)} Lógicos -> {num_physical_qubits} Físicos")

        return self._rebuild_circuit(circuit, logical_to_physical_map, resets_needed, num_physical_qubits)

    def _rebuild_circuit(self, original_circuit, mapping, resets, num_phys):
        qr_phys = QuantumRegister(num_phys, 'q_phys')
        new_qc = QuantumCircuit(qr_phys)
        
        # Mantenemos los registros clásicos idénticos
        for creg in original_circuit.cregs:
            new_qc.add_register(creg)

        reset_applied = set()

        for inst in original_circuit.data:
            op = inst.operation
            qargs = inst.qubits
            cargs = inst.clbits
            
            # Eliminamos las barreras originales, ya cumplieron su función lógica
            if op.name == 'barrier':
                continue
                
            new_qargs = []
            for q in qargs:
                if q not in mapping:
                    continue
                    
                phys_idx = mapping[q]
                
                # Insertar RESET si toca
                if resets[q] and q not in reset_applied:
                    new_qc.reset(qr_phys[phys_idx])
                    reset_applied.add(q)
                
                new_qargs.append(qr_phys[phys_idx])
            
            if new_qargs:
                new_qc.append(op, new_qargs, cargs)
            
        return new_qc

# --- EJEMPLO PARA PROBAR ---
qc = QuantumCircuit(4, 4)

# Tarea A 
qc.h(0)
qc.cx(0, 1)
qc.measure(0, 0)
qc.measure(1, 1)

# Usamos la barrera para decirle al algoritmo: "La Tarea B va DESPUÉS"
qc.barrier() 

# Tarea B 
qc.x(2)
qc.h(3)
qc.cx(2, 3)
qc.measure(2, 2)
qc.measure(3, 3)

compressor = DynamicCompressor()
qc_compressed = compressor.compress(qc)

print("\n--- Circuito Comprimido ---")
print(qc_compressed)