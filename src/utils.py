import numpy as np
import stim
from qldpc.circuits.noise_model import SI1000NoiseModel

def generate_stim_circuit(
        distance: int,
        error_rate: float,
        num_rounds: int):
    '''
    Generates a Stim circuit for an X-basis memory experiment of the rotated 
    surface code subject to SI1000 noise.

    Parameters:
        distance (int): surface code distance to generate the Stim circuit for.
        error_rate (float): error rate to use for the circuit's noise channels.
        num_rounds (int): number of error correction rounds to perform in the Stim circuit.
    
    Returns:
        circuit (stim.Circuit): the Stim circuit to be simulated
    '''
    d = distance
    circ = stim.Circuit.generated(
        "surface_code:rotated_memory_x", # correct Z errors
        rounds=num_rounds, # number of error correction rounds (typically d)
        distance=d
    )
    noise_model = SI1000NoiseModel(p=error_rate)
    return noise_model.noisy_circuit(circ)

def generate_syndromes_array(detector_shots, detectors_to_syndromes, distance, num_rounds):
    '''
    Generates an array of X syndrome bits corresponding to the X ancilla detector values sampled
    from a Stim circuit.

    Parameters:
        detector_shots (np.ndarray): the Stim detector shots to generate syndromes from
        detectors_to_syndromes (dict): map specifying how to convert Stim detectors to indices
                                       in the syndrome array
        distance (int): code distance of the Stim circuit
        num_rounds (int): number of rounds of detectors generated per Stim circuit shot

    Returns:
        syndrome_array (np.ndarray): an array of samples of X syndromes
    '''
    syndromes = np.zeros((len(detector_shots) * num_rounds, 
                          (distance+1)*((distance-1)//2)), dtype=np.uint8)

    rounds = []
    syndrome_indices = []

    # Iterate over each simulated shot and map detectors to syndrome indices
    for batch, detectors in enumerate(detector_shots):
        detector_ids = np.flatnonzero(detectors)
    
        # Populate syndrome array using detector data
        for id in detector_ids:
            # Only use X ancilla detectors for the Z error decoding problem
            try:
                round, inx = detectors_to_syndromes[id]
                rounds.append(batch*num_rounds + round)
                syndrome_indices.append(inx)
            except:
                continue
    
    syndromes[rounds, syndrome_indices] = 1

    return syndromes

def generate_errors_array(error_shots, errors_to_qubits, distance, num_rounds):
    '''
    Generates an array of data errors corresponding to Z errors sampled from a
    Stim circuit.

    Parameters:
        error_shots (np.ndarray): error shots sampled from the Stim circuit
        errors_to_qubits (dict): map specifying how to convert error IDs from Stim 
                                 to indices in the data error array
        distance (int): code distance simulated in the Stim circuit
        num_rounds (int): number of rounds of detectors generated per Stim circuit shot
    
    Returns:
        data_errors (np.ndarray): an array of data error samples
    '''
    data_errors = np.zeros((len(error_shots)*num_rounds, 
                            distance*distance), dtype=np.uint8)

    rounds = []
    error_indices = []

    # Map error instruction indices to data qubits
    for batch, errors in enumerate(error_shots):
        error_ids = np.flatnonzero(errors)

        for id in error_ids:
            # Only track Z-type errors on data qubits
            try:
                locs = errors_to_qubits[id]
                for (round, inx) in locs:
                    rounds.append(batch*num_rounds + round)
                    error_indices.append(inx)
            except:
                continue

    # Have to do this one by one so that repeat errors on the same
    # qubits cancel out in the XOR
    for i in range(len(rounds)):
        data_errors[rounds[i], error_indices[i]] ^= 1

    return data_errors

def generate_decoding_data(
        sampler: stim.CompiledDemSampler, 
        distance: int,
        num_shots: int,
        num_detector_rounds: int,
        detectors_to_syndromes: dict[int, tuple[int, int]],
        errors_to_qubits: dict[int, tuple[int, int]]) -> tuple[np.ndarray | None, np.ndarray, np.ndarray]:
    '''
    Generates samples of data errors and corresponding syndromes for a rotated surface code
    patch using Stim.

    Parameters:
        sampler (stim.CompiledDemSampler): used to sample errors from a Stim detector error model
        distance (int): surface code distance to generate samples for
        num_shots (int): number of shots to sample from the Stim detector error model
        num_detector_rounds (int): number of rounds of detectors generated per Stim circuit shot
        detectors_to_syndromes (dict): mapping from Stim detector IDs to indices in the generated syndrome array
        errors_to_qubits (dict): mapping from Stim error IDs to indices in the generated error array

    Returns:
        tuple of numpy arrays where the first array contains the sampled syndrome patterns,
        the second array contains the sample Stim circuit observable flips, the third array
        contains the sampled errors on data qubits, and the final array contains the sampled
        Stim detectors.
    '''
    # Sample errors and record detector events
    detector_shots, obs_shots, error_shots = sampler.sample(shots=num_shots,
                                                            return_errors=True)

    # Use samples to populate syndrome and data error arrays
    syndromes = generate_syndromes_array(detector_shots, detectors_to_syndromes, distance, num_detector_rounds)
    data_errors = generate_errors_array(error_shots, errors_to_qubits, distance, num_detector_rounds)
    
    return syndromes, obs_shots, data_errors, detector_shots
