# Source Code
This directory contains the core source code for the project which is used in the experiments. The two files are described below.

## predecoders.py
This file contains the implementations for the Clique and Pinball predecoders and is designed to (hopefully) be extended with new predecoders in the future. A generic `Predecoder` class is provided as a template specifying the expected functions to be implemented by a given predecoder. Any predecoder must inherit or implement its own version of the `decode_batch()`, `decode()`, and `is_logical_error()` functions. 

`decode_batch()` orchestrates decoding over a set of syndromes (typically $d$ rounds for code distance $d$), whereas `decode()` performs decoding over a pair of consecutive rounds. In both the Clique and Pinball predecoders, `decode_batch()` slides across the batch of $d$ rounds, two at a time, and calls `decode()` on each pair of syndrome rounds. Following decoding of a batch of syndromes, `is_logical_error()` can be used to compare the set of errors that occurred or the state of the Stim circuit's logical observable with the set of corrections produced by the predecoder to verify if a logical error was introduced. More details can be found in the respective functions within each predecoder's class definition.


## utils.py
This file contains useful utility functions related to running experiments, including constructing the Stim circuit to simulate for a given set of experimental parameters as well as the logic needed to sample data from that circuit.