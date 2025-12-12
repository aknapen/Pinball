import argparse
import numpy as np
import pickle

from os import makedirs, cpu_count, path
import sys
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '../')))

from multiprocessing import Pool
from math import floor
import json

from src import predecoders, utils

class Args():
    def __init__(self, distance, error_rate, predecoder, num_circuit_rounds, 
                 num_shots, detectors_to_syndromes, errors_to_qubits):
        self.distance: int = distance
        self.error_rate: float = error_rate
        self.predecoder: predecoders.Predecoder = predecoder
        self.num_circuit_rounds: int = num_circuit_rounds
        self.num_shots: int = num_shots
        self.detectors_to_syndromes: dict = detectors_to_syndromes
        self.errors_to_qubits: dict = errors_to_qubits

def sim(args: Args):
    circuit = utils.generate_stim_circuit(
        distance=args.distance,
        error_rate=args.error_rate,
        num_rounds=args.num_circuit_rounds
    )
    dem = circuit.detector_error_model(decompose_errors=True)
    sampler = dem.compile_sampler()
    num_detector_rounds = args.num_circuit_rounds + 1

    # Instantiate predecoder
    predecoder: predecoders.Predecoder = args.predecoder(args.distance, num_detector_rounds)

    # Simulation output statistics
    num_complex = 0
    logical_errors = 0

    # Iterate over batches of errors/syndromes
    for _ in range(args.num_shots):
        # We could generate all samples at the beginning and then iterate over them, which
        # might be faster since Stim will iterate in C instead of Python. However, Stim's 
        # sampling function has quite a bit of memory overhead as you increase the number of
        # shots and code distance, so it seems worth taking the small performance penalty
        # to keep memory consumption reasonably low
        syndrome_batch, observable_flip, error_batch, _ = utils.generate_decoding_data(
                                                sampler=sampler,
                                                distance=args.distance,
                                                num_shots=1, 
                                                num_detector_rounds=num_detector_rounds,
                                                detectors_to_syndromes=args.detectors_to_syndromes,
                                                errors_to_qubits=args.errors_to_qubits,
                                            )
        
        # If the batch is all zeros, the predecoder will definitely succeed, so skip
        if not np.any(syndrome_batch):
            continue

        # Determine batch corrections and if batch was complex
        l1_corrections, batch_complex = predecoder.decode_batch(syndrome_batch)
        
        # If complex, L1 will have deferred to L2 decoder, so don't
        # analyze correction results
        if batch_complex:
            num_complex += 1
        else:
            if predecoder.is_logical_error(error_batch, l1_corrections, observable_flip[0][0]):
                logical_errors += 1
            
    return (logical_errors, num_complex)

def run_simulation(distances, error_rates, predecoder, num_shots, output_dir):
    for d in distances:
        num_circuit_rounds = d

        # Make sure the simulation output directory exists
        dirname = output_dir + f"d={d}/"
        makedirs(dirname, exist_ok=True)

        detectors_to_syndromes = None
        errors_to_qubits = None
        
        # Retrieve mappings of Stim detectors/errors to our syndromes/errors
        metadir = f"../metadata/d={d}/"
        with open(metadir + "detectors_to_syndromes_map.pkl", "rb") as f:
            detectors_to_syndromes = pickle.load(f)
        with open(metadir + "errors_to_qubits_map.pkl", "rb") as f:
            errors_to_qubits = pickle.load(f)

        for e in error_rates:
            outfile = dirname + f"e={e:.4f}.json"
            num_threads = cpu_count()-1

            print(f"Code distance: {d}, error_rate: {e}, predecoder: {predecoder.__name__}, " + 
                  f"num_shots: {num_shots}, output_dir: {output_dir}, num_threads: {num_threads}")
            
            # Divide up decoding workloads into batches for each thread
            num_shots_per_thread = floor(num_shots / num_threads)
            remaining_shots = num_shots % num_threads

            # Configure simulation parameters to provide to each thread
            thread_args = []
            for t in range(num_threads):
                if t < num_threads - 1:
                    args = Args(d, e, predecoder, num_circuit_rounds, 
                                num_shots_per_thread, detectors_to_syndromes, errors_to_qubits)
                # Last thread may have some extra batches to process
                else:
                    args = Args(d, e, predecoder, num_circuit_rounds,
                                num_shots_per_thread+remaining_shots,
                                detectors_to_syndromes, errors_to_qubits)
                
                thread_args.append(args)
          
            # Divide simulation shots over the available threads in the system
            with Pool(num_threads) as p:
                sim_data = p.map(sim, thread_args)
                
                # Error count statistics
                logical_errors = sum([data[0] for data in sim_data])
                # Coverage statistics
                num_complex = sum([data[1] for data in sim_data])

                # Number of non-complex batches
                num_simple = num_shots - num_complex
                coverage = (num_simple / num_shots) * 100

                # L1 accuracy only has meaning if the predecoder was ever used
                if num_simple > 0:
                    accuracy  = (1 - (logical_errors / num_simple)) * 100
                else:
                    accuracy = 0
                
                print(f"# Complex Shots = {num_complex}, # Logical Errors = {logical_errors}, " +
                      f"L1 Coverage (%) = {coverage}, # L1 Accuracy (%) = {accuracy}\n")

                results = {
                    "l1_accuracy": accuracy,
                    "l1_coverage": coverage,
                    "num_shots": num_shots
                }

                with open(outfile, "w") as f:
                    json.dump(results, f, indent=4)

def parse_simulation_args():
    parser = argparse.ArgumentParser()

    # Parse command-line options
    parser.add_argument("-f", "--arg_file", help="Path to JSON file containing simulation arguments")
    parser.add_argument("-d", "--distances", help="Code distances to simulate", nargs="*")
    parser.add_argument("-e", "--error_rates", help="Physical error rates to simulate", nargs="*")
    parser.add_argument("-p", "--predecoder", help="Predecoder to simulate", choices=["Clique", "Pinball"],
                        default="Pinball")
    parser.add_argument("-n", "--num_shots", type=int, help="Number of Stim circuit shots to simulate")
    parser.add_argument("-o", "--output_dir", help="Output statistics directory")

    args = parser.parse_args()
    
    # Parse JSON file containing simulation arguments
    if args.arg_file:
        with open(args.arg_file, "r") as f:
            sim_args = json.load(f)

            try:
                distances = sim_args["distances"]
                error_rates = sim_args["error_rates"]
                predecoder = sim_args["predecoder"]
                num_shots = sim_args["num_shots"]
                output_dir = sim_args["output_dir"]
            
            except Exception as e:
                print("[ERROR] The following exception was raised while parsing simulation arguments")
                print(e)
                print("This is possibly due to omitting necessary arguments in the input JSON file.")
                exit(1)
    # Parse command-line containing simulation arguments
    else:
        # Defaults
        distances = [3,5,7,9]
        error_rates = [0.01, 0.005, 0.001, 0.0005, 0.0001]
        predecoder = "Pinball"
        num_shots = 100000
        output_dir = "stats/"

        if args.distances:
            distances = [int(d) for d in args.distances]

        if args.error_rates:
            error_rates = [float(e) for e in args.error_rates]
        
        if args.predecoder:
            predecoder = args.predecoder
        
        if args.num_shots:
            num_shots = args.num_shots
        
        if args.output_dir:
            output_dir = args.output_dir     
    
    for d in distances:
        if not (d % 2):
            print("[ERROR] Only odd code distances can be simulated.")
            exit(1)
        elif d < 0:
            print("[ERROR] Negative code distance specified.")
            exit(1)

    for e in error_rates:
        if e < 0:
            print("[ERROR] Negative physical error rate specified.")
            exit(1)

    if predecoder == "Clique":
        predecoder = predecoders.Clique
    elif predecoder == "Pinball":
        predecoder = predecoders.Pinball
    elif predecoder == "None":
        print(f"[ERROR] Cannot specify None for predecoder in L1 statistics experiment.")
        exit(1)
    else:
        print(f"[ERROR] Unrecognized predecoder {predecoder}.")
        exit(1)
        
    if output_dir[-1] != "/":
        output_dir += "/"    
    output_dir += f"l1_statistics/{predecoder.__name__}/"

    return (distances, error_rates, predecoder, num_shots, output_dir)

def main():
    (distances, error_rates, predecoder, num_shots, output_dir) = parse_simulation_args()

    run_simulation(distances, error_rates, predecoder, num_shots, output_dir)

if __name__ == "__main__":
    main()