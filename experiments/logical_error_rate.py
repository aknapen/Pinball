import argparse
import numpy as np
import pymatching
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
        self.predecoder: predecoders.Predecoder | None = predecoder
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
    
    # Instantiate decoder/predecoder
    mwpm = pymatching.Matching(dem)
    use_l1 = True
    if args.predecoder is None:
        use_l1 = False
    else:
        predecoder: predecoders.Predecoder = args.predecoder(args.distance, num_detector_rounds)

    # Simulation output statistics
    num_l1_shots = 0
    num_l2_shots = 0
    l1_errors = 0
    l2_errors = 0

    # Iterate over batches of errors/syndromes
    for _ in range(args.num_shots):
        # We could generate all samples at the beginning and then iterate over them, which
        # might be faster since Stim will iterate in C instead of Python. However, Stim's 
        # sampling function has quite a bit of memory overhead as you increase the number of
        # shots and code distance, so it seems worth taking the small performance penalty
        # to keep memory consumption reasonably low
        syndrome_batch, observable_flip, error_batch, detectors = utils.generate_decoding_data(
                                                sampler=sampler,
                                                distance=args.distance,
                                                num_shots=1, 
                                                num_detector_rounds=num_detector_rounds,
                                                detectors_to_syndromes=args.detectors_to_syndromes,
                                                errors_to_qubits=args.errors_to_qubits,
                                            )
        
        # If the batch is all zeros, both L1 and L2 will definitely succeed, so skip
        if not np.any(syndrome_batch):
            if use_l1:
                num_l1_shots += 1
            else:
                num_l2_shots += 1
            continue
        
        decoded = False
        if use_l1:
            l1_corrections, batch_complex = predecoder.decode_batch(syndrome_batch=syndrome_batch)
            
            # Commit predecoder corrections if the batch was not complex
            if not batch_complex:
                decoded = True
                num_l1_shots += 1

                if predecoder.is_logical_error(error_batch, l1_corrections, observable_flip[0][0]):
                    l1_errors += 1
        
        # We either aren't simulating the predecoder or the batch was complex
        if not decoded:
            num_l2_shots += 1
            l2_pred = mwpm.decode(detectors.T)

            if l2_pred[0] != observable_flip[0][0]:
                l2_errors += 1

    return (l1_errors, num_l1_shots, l2_errors, num_l2_shots)

def run_simulation(distances, error_rates, predecoder, num_shots, output_dir, sim_id):
    for d in distances:
        num_circuit_rounds = d
        
        # Retrieve mappings of Stim detectors/errors to our syndromes/errors
        metadir = f"../metadata/d={d}/"
        with open(metadir + "detectors_to_syndromes_map.pkl", "rb") as f:
            detectors_to_syndromes = pickle.load(f)
        with open(metadir + "errors_to_qubits_map.pkl", "rb") as f:
            errors_to_qubits = pickle.load(f)

        for e in error_rates:

            # Make sure the simulation output directory exists
            dirname = output_dir + f"d={d}/e={e:.4f}/"
            makedirs(dirname, exist_ok=True)
            
            outfile = dirname + f"{sim_id}.json"
            num_threads = cpu_count()-1

            print(f"Code distance: {d}, error_rate: {e}, " + 
                  f"predecoder: { 'None' if predecoder is None else predecoder.__name__}, " +
                  f"num_shots: {num_shots}, output_dir: {output_dir}, num_threads: {num_threads}, " +
                  f"sim_id: {sim_id}")
            
            # Divide up decoding workloads into batches for each thread
            num_shots_per_thread = floor(num_shots / num_threads)
            remaining_shots = num_shots % num_threads
            
            # Configure simulation parameters to provide to each thread
            thread_args = []
            for t in range(num_threads):
                if t < num_threads - 1:
                    args = Args(d, e, predecoder, num_circuit_rounds, num_shots_per_thread, 
                                detectors_to_syndromes, errors_to_qubits)
                # Last thread may have some extra batches to process
                else:
                    args = Args(d, e, predecoder, num_circuit_rounds,
                                num_shots_per_thread+remaining_shots, detectors_to_syndromes, 
                                errors_to_qubits)
                
                thread_args.append(args)
          
            # Divide simulation shots over the available threads in the system
            with Pool(num_threads) as p:
                sim_data = p.map(sim, thread_args)
                
                # Error count statistics
                num_l1_errors = sum([data[0] for data in sim_data])
                num_l1_shots = sum([data[1] for data in sim_data])
                num_l2_errors = sum([data[2] for data in sim_data])
                num_l2_shots = sum([data[3] for data in sim_data])

                logical_error_rate = (num_l1_errors + num_l2_errors) / (num_l1_shots + num_l2_shots)

                print(f"# Shots = {num_l1_shots + num_l2_shots}, Logical Error Rate = {logical_error_rate}, " +
                      f"# L1 shots = {num_l1_shots}, # Total L1 errors = {num_l1_errors}, " +
                      f"# L2 shots = {num_l2_shots}, # Total L2 errors = {num_l2_errors}\n")

                results = {
                    "logical_error_rate": logical_error_rate,
                    "num_l1_errors": num_l1_errors,
                    "num_l1_shots": num_l1_shots,
                    "num_l2_errors": num_l2_errors,
                    "num_l2_shots": num_l2_shots,
                    "num_total_shots": num_shots
                }

                with open(outfile, "w") as f:
                    json.dump(results, f, indent=4)

def parse_simulation_args():
    parser = argparse.ArgumentParser()

    # Parse command-line options
    parser.add_argument("-f", "--arg_file", help="Path to JSON file containing simulation arguments")
    parser.add_argument("-d", "--distances", help="Code distances to simulate", nargs="*")
    parser.add_argument("-e", "--error_rates", help="Physical error rates to simulate", nargs="*")
    parser.add_argument("-l1", "--predecoder", help="Predecoder to simulate", 
                        choices=["Clique", "Pinball", "None"],
                        default="Pinball")
    parser.add_argument("-n", "--num_shots", type=int, default=100000,
                        help="Number of Stim circuit shots to simulate")
    parser.add_argument("-o", "--output_dir", help="Output statistics directory")
    parser.add_argument("-i", "--sim_id", type=int, default=0,
                        help="An integer ID for the simulation. This allows creating distinct " + 
                             "output files for simulations, enabling separate simulation instances " + 
                             "to run in parallel).")
    
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
                sim_id = sim_args["sim_id"]
            
            except Exception as e:
                print("[ERROR] The following exception was raised while parsing simulation arguments")
                print(e)
                print("This is possibly due to omitting necessary arguments in the input JSON file.")
                exit(1)
    else:
        # Defaults
        distances = [3,5,7,9]
        error_rates = [0.01, 0.005, 0.001, 0.0005, 0.0001]
        num_shots = 100000
        predecoder = "Pinball"
        output_dir = "stats/"
        sim_id = 0

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

        if args.sim_id:
            sim_id = args.sim_id
    
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
        predecoder = None
    else:
        print(f"[ERROR] Unrecognized predecoder {predecoder}.")
        exit(1)

    if output_dir[-1] != "/":
        output_dir += "/"

    if predecoder is not None:
        output_dir += f"logical_error_rate/{predecoder.__name__}/"
    else:
        output_dir += f"logical_error_rate/None/"

    return (distances, error_rates, predecoder, num_shots, output_dir, sim_id)

def main():
    (distances, error_rates, predecoder, num_shots, output_dir, sim_id) = parse_simulation_args()

    run_simulation(distances, error_rates, predecoder, num_shots, output_dir, sim_id)

if __name__ == "__main__":
    main()