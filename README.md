# Pinball
This repository contains the source code for the Pinball predecoder, a cryogenic hardware predecoder for surface code quantum error correction decoding under circuit-level noise. Details about Pinball can be found in [the arXiv paper](https://arxiv.org/abs/2512.09807). In addition, code is provided for reproducding many of the experimental results/figures from the paper.

## Installation
1. Clone the repository:

```
git clone git@github.com:aknapen/Pinball.git
```

2. Install the required Python dependencies within your Python environment using:

```
pip install requirements.txt
```

## Repository Organization
The repository is organized into the following three directories:
- `src/`: core source code for the Pinball and CLique predecoder implementations as well as some utility functions.

- `experiments/`: code for running experiments to reproduce key results from the paper.

- `metadata/`: useful metadata used across the different experiments.

More details are provided in the respective READMEs within each directory.

## Hardware Dependencies
This code should be compatible to run on any device. Multithreading support for experiments should work out-of-the-box using `Pools` from Python's built-in `multiprocessing` library. It is recommended to run experiments requring many simulation shots (e.g., due to large code distances or low physical error rates) on a machine with many threads available. The experiments used for the paper still took many hours to complete using 256 threads.