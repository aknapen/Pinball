# Experiments

This directory contains the code needed to experiments to generate many of the results presented in the Pinball paper. In the below text, MWPM refers to the Pymatching decoder. Here is a brief overview of the four experiments:

1. `l1_statistics.py`: can be used to estimate L1 coverage and accuracy metrics for the Pinball and Clique predecoders (Fig. 19 and 21 in the paper). 

2. `logical_error_rate.py`: can be used to estimate logical error rates for Pinball+MWPM, Clique+MWPM, and MWPM-only (Fig. 22 and 24 in the paper).

3. `chain_length_distribution.py`: can be used to estimate the distribution of lengths of error chains at different code distances and physical error rates (Fig. 6 in the paper).

4. `error_frequency_distribution.py`: can be used to estimate the distribution of different classes of errors (space-like, time-like, single-qubit spacetime-like, and hook-like) at different code distances and physical error rates (Tab. II in the paper).

## Specifying Experimental Arguments

The experiment files contains a `parse_simulation_args()` function with more details on experiment-specific parameters that can be passed in via the command line. An example of running the `l1_statistics.py` experiment using command-line arguments is shown below:

```
python3 l1_statistics.py -d 3 5 7 9 -e 0.0001 0.001 0.01 -p Pinball -n 100000
```

This command will run simulations to estimate Pinball's L1 coverage and accuracy for code distances 3, 5, 7, and 9. At each code distance, the simulation will be run for three physical error rates: $10^{-4}$, $10^{-3}$, and $10^{-2}$, and for each simulation, 100,000 shots will be simulated.

Since manually specifying all of these parameters for each experiment can get tedious, you can alternatively specify arguments in a JSON file; the file `example_args.json` provides an example. This JSON file contains the complete set of options across all experiments, so it can be reused for any experiment you want to run. To run the `l1_statistics.py` experiment using command-line arguments specified in a JSON file, you can run:

```
python3 l1_statistics.py -f example_args.json
```

## Experiment Runtime and Parallelization
It is important to note that, for the `l1_statistics.py` and `logical_error_rate.py` experiments, potentially many simulation shots will be needed to obtain accurate estimates for the results, particularly at high code distances and/or low physical error rates. For the Pinball paper, up to $10^7$ simulation shots were used per (code distance, physical error rate) pair to estimate L1 statistics, whereas for logical error rate simulations, that number grew to $10^9$! 

This large number of simulation shots translates into long, long simulation times. Luckily, since each simulation shot is independent of all others, simulations are highly amenable to parallelization over multiple threads. All of the experiments are set up to use `Pools` from Python's `multiprocessing` module to batch execute experiments over $N-1$ threads, where $N$ is the value returned when running Python's `cpu_count()` function.

Despite the benefits of parallelization, simulations, particularly at high code distanceds, can still take a long time. Using a high-performance compute node with 256 threads, gathering L1 statistics at a code distance of 21 still took somewhere around 8-9 hours to complete, and simulating logical error rates beyond code distance 11 was unfeasible. Keep this in mind when configuring experiments you want to run.

## Collecting Experiment Results
By default, experimental results are collected into the directory `./stats/<experiment_name>/`. Within a given experiment's directory, results will be further organized into subdirectories. In cases where predecoders are being simulated, the first subdirectory will correspond to the name of the predecoder. Therafter, results are organized by code distance, and in the case of the `logical_error_rates.py` experiment, by physical error rate. The latter allows for running multiple logical error rate simulations in parallel without overwriting any results (use the `sim_id` argument to configure separate simulation runs). As a more concrete example, if running the following command:

```
python3 logical_error_rate.py -d 3 -e 0.001 -p Pinball
```

you should expect to find your results in the directory `./stats/logical_error_rate/Pinball/d=3/e=0.0010/0.json`. If you prefer to save your simulation results to a directory other than `./stats`, this can be configured using the `output_dir` simulation argument.