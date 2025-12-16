# Verilog Implementation Directory (`verilog/`)

This directory contains the SystemVerilog design files specifying Pinball's hardware implementation. The two primary files are described below.

---

## `pinball.sv`

This is the top-level module for Pinball which specifies the control signal flow through the pipeline architecture. The stages in this file correspond to the predecoding stages described in the paper.

## `leaf_decode.sv`

This file contains the module describing the predecoding primitive, the fundamental unit of logic in Pinball. It consists of a very simple 2-stage combinational circuit. The top-level module instantiates many of these predecoding primitives in each pipeline stage using `generate` blocks.