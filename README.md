# Pinball: A Cryogenic Hardware Predecoder

[![arXiv](https://img.shields.io/badge/Paper-2512.09807-B31B1B?style=flat-square)](https://arxiv.org/abs/2512.09807)

This repository contains the source code for **Pinball**, a cryogenic hardware predecoder for surface code quantum error correction (QEC) decoding under circuit-level noise. Pinball is designed to circumvent key QEC bandwidth and power bottlenecks in highly-constrained, cryogenic environments while maintaining the high QEC performance required for fault-tolerant qunatum computing.

Details about Pinball and its performance can be found in [the comprehensive arXiv paper](https://arxiv.org/abs/2512.09807). In addition to Pinball's core logic, this repository provides code and scripts for reproducing many of the experimental results and figures from the paper.

---

## 🚀 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:aknapen/Pinball.git
    ```

2.  **Install Python Dependencies:**
    Navigate to the repository directory and install the required packages.

    > **⚠️ Note:** The required [qLDPC](https://github.com/qLDPCOrg/qLDPC) package imposes a minimum requirement of **Python >= 3.10**.

    ```bash
    pip install requirements.txt
    ```

---

## 📂 Repository Organization

The project is organized into three main directories for clarity:

| Directory | Purpose |
| :--- | :--- |
| `src/` | Core Python source code for functionally modeling the **Pinball** and **Clique** predecoder implementations, along with essential utility functions. |
| `experiments/` | Scripts and code for running simulations and experiments to reproduce key results and figures from the paper. |
| `metadata/` | Useful configuration files and static data/metadata used across the different experiments. |

More detailed information, including specific usage instructions, is provided in the respective `README` files within each directory.

---

## ⚙️ Hardware Dependencies & Performance

This code is designed to be compatible to run on any device using standard Python dependencies.

For experiments requiring significant computational resources (e.g., those needing many simulation shots due to large code distances or low physical error rates), **multithreading is highly recommended.**

* Multithreading support is included out-of-the-box using `Pools` from Python's built-in `multiprocessing` library.
* The original experiments used for the paper still required many hours to complete, even when utilizing 256 threads. It is recommended to run such experiments on a machine with many available cores.