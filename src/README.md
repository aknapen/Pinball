# Source Code Directory (`src/`)

This directory contains the core Python source code for the entire project, which is utilized by the experiment scripts in the `experiments/` directory. The two primary files are described below.

---

## `predecoders.py`

This file contains the core logic and implementations for the Clique and Pinball predecoders. It is designed to be easily extensible to include new predecoders in the future.

### Generic `Predecoder` Class

A generic `Predecoder` class is provided as a foundational template. Any new predecoder implementation must inherit from this class or implement its own versions of the following three required functions:

* `decode_batch()`
* `decode()`
* `is_logical_error()`

### Functionality Details

| Function | Description |
| :--- | :--- |
| `decode_batch()` | Orchestrates the entire decoding process over a batch of syndromes (typically $d$ rounds for a code distance $d$). |
| `decode()` | Executes the fundamental predecoding logic over a pair of **consecutive syndrome rounds**. |
| `is_logical_error()` | Verifies if a logical error has occurred by comparing the set of corrections produced by the predecoder against the actual errors that occurred or the state of the Stim circuit's logical observable. |

> **Process Flow:** In both the Clique and Pinball implementations, `decode_batch()` sequentially slides across the batch of $d$ rounds, two at a time, and calls `decode()` on each pair of syndrome rounds.

More specific implementation details can be found in the respective function definitions within each predecoder's class.

---

## `utils.py`

This file contains essential utility functions related to running and setting up experiments, including:

* Logic for constructing the Stim circuit to simulate, based on a given set of experimental parameters.
* Functions needed to sample data (e.g., syndromes, errors, logical observables) directly from that constructed circuit.