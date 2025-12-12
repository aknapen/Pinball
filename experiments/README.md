# Experiments Directory

This directory contains the necessary code to **run experiments** and generate many of the key results presented in the Pinball paper. In the text below, **MWPM** refers to the **Pymatching Decoder**.

---

## Overview of Experiments

| File | Purpose | Corresponding Paper Figures/Tables |
| :--- | :--- | :--- |
| `l1_statistics.py` | Estimates L1 coverage and accuracy metrics for the Pinball and Clique predecoders. | Fig. 19 and 21 |
| `logical_error_rate.py` | Estimates logical error rates for Pinball+MWPM, Clique+MWPM, and MWPM-only decoding schemes. | Fig. 22 and 24 |
| `chain_length_distribution.py` | Estimates the distribution of lengths of error chains at different code distances and physical error rates. | Fig. 6  |
| `error_frequency_distribution.py` | Estimates the distribution of different classes of errors (space-like, time-like, single-qubit spacetime-like, and hook-like). | Tab. II |

---

## Specifying Experimental Arguments

Experiments can be configured by passing parameters via the command line or by using a JSON configuration file.

### 1. Command Line Arguments

Each experiment file contains a `parse_simulation_args()` function that provides detailed documentation on experiment-specific parameters.

**Example: Running `l1_statistics.py`**

```bash
python3 l1_statistics.py -d 3 5 7 9 -e 0.0001 0.001 0.01 -p Pinball -n 100000
```

This command will estimate Pinball's L1 coverage and accuracy for code distances 3, 5, 7, and 9. At each code distance, the simulation will run for three physical error rates (10−4, 10−3, and 10−2), with 100,000 shots simulated for each unique parameter set.

### 2. JSON Configuration File

To avoid manually specifying a large number of parameters, arguments can be provided in a JSON file. The file `example_args.json` provides a template. This JSON file contains the complete set of options across all experiments and can be reused.

**Example: Running with JSON**
```bash
python3 l1_statistics.py -f example_args.json
```

## Experiment Runtime and Parallelization

Accurate results, particularly for `l1_statistics.py` and `logical_error_rate.py`, may require a substantial number of simulation shots, especially at high code distances or low physical error rates. For context, the experimental results from the paper required up to $10^7$ shots for `l1_statistics.py` and up to $10^9$ shots for `logical_error_rate.py` per (code distance, physical error rate) pair!

**Parallelization**

Fortunately, simulations are highly amenable to parallelization because each Stim circuit shot is independent. All experiments are configured to use `Pools` from Python's `multiprocessing` module. Experiments execute across $N−1$ threads, where $N$ is the value returned by python's `cpu_count()` function.

Despite parallelization, simulations at high code distances can be extremely time-consuming: gathering L1 statistics at a code distance of 21 took 8-9 hours on a high-performance compute node with 256 threads, and simulating logical error rates beyond code distance 11 was unfeasible. Keep these runtimes in mind when configuring your experiments.


## Collecting Experimental Results
By default, experimental results are saved into the directory structure `./stats/<experiment_name>/`. If you prefer to save your results to a directory other than `./stats`, you can configure this using the `output_dir` simulation argument.

**Output Directory Structure**

The organization of subdirectories depends on the experiment being run:

1. Predecoder: When predecoders are simulated, the first subdirectory will be the name of the predecoder (e.g., Pinball).

2. Code Distance: Thereafter, results are organized by code distance (e.g., `d=3/`).

3. Physical Error Rate: For `logical_error_rate.py`, results are further organized by physical error rate (e.g., `e=0.0010/`). This is done to allow multiple separate simulation instances to be run in parallel without overwriting each others' results. This is particularly useful for logical error rate experiments requiring a very large number of simulation shots. 

> **Note**: To ensure separate simulations output to separate files, specify a separate `sim_id` simulation argument for each.

**Example File Path**

The following command will store simulation results in `./stats/logical_error_rate/Pinball/d=3/e=0.0010/0.json`:

```bash
python3 logical_error_rate.py -d 3 -e 0.001 -p Pinball
```
