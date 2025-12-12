# Metadata Directory

This directory contains various serialized metadata structures (Python dictionaries saved as `.pkl` files) that are used to significantly speed up simulations by precomputing complex mappings derived from the Stim surface code circuits. Brief explanations for each file are provided below.

> **Note:** Since only $Z$ errors are simulated, the translations specified below are only valid for detectors corresponding to $X$ ancilla qubits and circuit errors that flip those detectors.

---

## Metadata Files

### `detectors_to_syndromes_map.pkl`

This file contains a mapping essential for bridging the gap between Stim's default detector ordering and the predecoders' required input format.

* **Context:** The Pinball and Clique predecoders expect syndromes in a flat numpy array organized in row-major order, which differs from the ordering of detectors specified in the default Stim circuits.
* **Purpose:** Translates Stim detector IDs to their corresponding positions in the syndrome input array required by the Pinball and Clique predecoders.
* **Mapping:** `detectors_to_syndromes_map[detector_id] -> (syndrome_round, index_within_round)`

### `errors_to_qubits_map.pkl`

This mapping is critical for verification by linking circuit errors back to the data qubits they corrupt.

* **Context:** When sampling a Stim circuit, Stim returns only error IDs corresponding to the error instructions in the circuit's detector error model. This dictionary specifies the final effect on data qubits due to an error (e.g., a hook error on an ancilla qubit ultimately flips two data qubits).
* **Purpose:** Maps a Stim error ID to the list of data qubits that were flipped due to that error.
* **Mapping:** `errors_to_qubits_map[error_id] -> ([rounds], [qubit_indices_within_rounds])`

### `errors_to_dem_components.pkl`

Used specifically for the `error_frequency_distribution.py` experiment to categorize errors based on their decoding graph signature.

* **Purpose:** Translates a Stim error ID into the relative spatial and temporal positioning components between the pair of flipped detectors in the decoding graph.
* **Mapping:** `errors_to_dem_components[error_id] -> (spatial_component, temporal_component)`
* **Example:** For a time-like error, the dictionary will return `(0, 1)`.

### `errors_to_detectors.pkl`

Used specifically for the `chain_length_distribution.py` experiment to identify connected error chains.

* **Context:** By knowing which errors share a common detector, they can be linked together to form longer error chains for analysis.
* **Purpose:** Maps a Stim error ID to the set of detectors that were flipped by that error.
* **Mapping:** `errors_to_detectors[error_id] -> [detector_ids]`