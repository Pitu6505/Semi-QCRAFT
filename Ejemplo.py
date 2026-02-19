from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.transpiler import CouplingMap

class AdvancedTopologyCompressor:
    def __init__(self, coupling_map=None):
        self.coupling_map = coupling_map

    def _advance_measurements(self, circuit):
        last_gate_idx = {q: -1 for q in circuit.qubits}
        measures = {} 
        
        for i, inst in enumerate(circuit.data):
            if inst.operation.name == 'measure':
                measures[inst.qubits[0]] = inst.clbits[0]
            elif inst.operation.name != 'barrier': 
                for q in inst.qubits:
                    last_gate_idx[q] = i
                    
        new_qc = QuantumCircuit(*circuit.qregs, *circuit.cregs)
        measured_qubits = set()
        
        for i, inst in enumerate(circuit.data):
            if inst.operation.name == 'measure':
                continue 
                
            new_qc.append(inst.operation, inst.qubits, inst.clbits)
            
            for q in inst.qubits:
                if last_gate_idx[q] == i and q in measures and q not in measured_qubits:
                    new_qc.measure(q, measures[q])
                    measured_qubits.add(q)
                    
        for q, c in measures.items():
            if q not in measured_qubits:
                new_qc.measure(q, c)
                measured_qubits.add(q)
                
        return new_qc

    def _get_qubit_lifetimes(self, circuit):
        qubit_lifetimes = {q: {'start': float('inf'), 'end': -1} for q in circuit.qubits}
        qubit_current_time = {q: 0 for q in circuit.qubits}
        
        for inst in circuit.data:
            qargs = inst.qubits
            if not qargs:
                continue
                
            start_time = max(qubit_current_time[q] for q in qargs)
            
            # ¡CORRECCIÓN AQUÍ! La barrera actualiza el reloj de todos sus qubits
            if inst.operation.name == 'barrier':
                for q in qargs:
                    qubit_current_time[q] = start_time
                continue
                
            end_time = start_time + 1
            
            for q in qargs:
                if qubit_lifetimes[q]['start'] == float('inf'):
                    qubit_lifetimes[q]['start'] = start_time
                qubit_lifetimes[q]['end'] = end_time
                qubit_current_time[q] = end_time
                
        return qubit_lifetimes

    def _rebuild_circuit(self, original_circuit, mapping, resets, num_phys):
        qr_phys = QuantumRegister(num_phys, 'q_phys')
        new_qc = QuantumCircuit(qr_phys)
        for creg in original_circuit.cregs:
            new_qc.add_register(creg)

        reset_applied = set()

        for inst in original_circuit.data:
            if inst.operation.name == 'barrier':
                continue
                
            new_qargs = []
            for q in inst.qubits:
                phys_idx = mapping[q]
                
                if resets[q] and q not in reset_applied:
                    new_qc.reset(qr_phys[phys_idx])
                    reset_applied.add(q)
                    
                new_qargs.append(qr_phys[phys_idx])
            
            if new_qargs:
                new_qc.append(inst.operation, new_qargs, inst.clbits)
                
        return new_qc

    def compress_and_map(self, circuit):
        print(f"1. Circuito Original: {circuit.num_qubits} qubits lógicos.")
        
        qc_early = self._advance_measurements(circuit)
        print("2. Medidas adelantadas con éxito.")
        
        lifetimes = self._get_qubit_lifetimes(qc_early)
        sorted_qubits = sorted(lifetimes.keys(), key=lambda q: lifetimes[q]['start'])
        
        physical_lanes_end_time = []
        logical_to_physical_map = {}
        resets_needed = {}

        for logical_q in sorted_qubits:
            start = lifetimes[logical_q]['start']
            end = lifetimes[logical_q]['end']
            if start == float('inf'): continue
                
            assigned = False
            for lane_idx, lane_end_time in enumerate(physical_lanes_end_time):
                if lane_end_time <= start:
                    physical_lanes_end_time[lane_idx] = end
                    logical_to_physical_map[logical_q] = lane_idx
                    resets_needed[logical_q] = True
                    assigned = True
                    break
            
            if not assigned:
                physical_lanes_end_time.append(end)
                logical_to_physical_map[logical_q] = len(physical_lanes_end_time) - 1
                resets_needed[logical_q] = False

        num_phys = len(physical_lanes_end_time)
        qc_compressed = self._rebuild_circuit(qc_early, logical_to_physical_map, resets_needed, num_phys)
        print(f"3. Compresión Dinámica completada: de {circuit.num_qubits} a {num_phys} qubits físicos.")
        
        if self.coupling_map:
            print("4. Adaptando a la topología de la máquina física...")
            qc_mapped = transpile(qc_compressed, 
                                  coupling_map=self.coupling_map, 
                                  optimization_level=3, 
                                  routing_method='sabre')
            print(f"   -> Mapeo completado. Listo para enviar a IBM/AWS.")
            return qc_mapped
        else:
            return qc_compressed


# ==========================================
# PRUEBA CORREGIDA
# ==========================================
mapa_simulado = CouplingMap([[0, 1], [1, 0], [1, 2], [2, 1], [2, 3], [3, 2]])

qc = QuantumCircuit(4, 4)

qc.h(0)
qc.cx(0, 1)

qc.barrier() 

qc.x(2)
qc.cx(2, 3)

qc.measure([0, 1, 2, 3], [0, 1, 2, 3])

print("\n--- INICIANDO PROCESO DE OPTIMIZACIÓN ---")
compressor = AdvancedTopologyCompressor(coupling_map=mapa_simulado)
print("Circuito Original:")
print(qc)
circuito_final_optimizado = compressor.compress_and_map(qc)

print("\n--- CIRCUITO FINAL OPTIMIZADO PARA HARDWARE ---")
print(circuito_final_optimizado)