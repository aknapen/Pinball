import argparse
import numpy as np
import pickle

from os import makedirs, cpu_count, path
import sys
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '../')))

from multiprocessing import Pool
from math import floor
import json

import stim

from src import utils

class SimArgs():
    def __init__(self, dem, num_shots, error_map):
        self.dem: stim.DetectorErrorModel = dem
        self.num_shots: int = num_shots
        self.error_map: dict = error_map

def sim(args: SimArgs):
    sampler = args.dem.compile_sampler()
    # 3 options for spacelike error lengths [0, 1, 2], 2 for time [0, 1]
    distribution = np.zeros((3, 2), dtype=np.uint64)
    total_errors = 0

    for _ in range(args.num_shots):
        _, _, shot = sampler.sample(shots=1, return_errors=True)
        error_ids = np.flatnonzero(shot)

        # Only care about Z errors here
        for id in error_ids:
            try:
                spacelike_component, timelike_component = args.error_map[id]
                distribution[spacelike_component][timelike_component] += 1
                total_errors += 1
            except:
                continue
    
    return distribution, total_errors

def run_simulation(distances, error_rates, num_shots, output_dir):
    for d in distances:
        # Make sure the simulation output directory exists
        dirname = output_dir + f"d={d}/"
        makedirs(dirname, exist_ok=True)
        
        fname = f"../metadata/d={d}/errors_to_dem_components.pkl"
        with open(fname, "rb") as f:
            error_map = pickle.load(f)
        
        for e in error_rates:
            outfile = dirname + f"e={e:.4f}.json"
            num_threads = cpu_count()-1

            print(f"Code distance: {d}, error_rate: {e}, num_shots: {num_shots}, " +
                    f"output_dir: {output_dir}, num_threads: {num_threads}")

            # Create Stim circuit for this particular simulation
            circuit = utils.generate_stim_circuit(
                distance=d, 
                error_rate=e,
                num_rounds=d
            )
            dem = circuit.detector_error_model(decompose_errors=True)

            # Divide up decoding workloads into batches for each thread
            num_shots_per_thread = floor(num_shots / num_threads)
            remaining_shots = num_shots % num_threads

            # Configure simulation parameters to provide to each thread
            thread_args = []
            for t in range(num_threads):
                if t < num_threads - 1:
                    args = SimArgs(dem, num_shots_per_thread, error_map)
                # Last thread may have some extra batches to process
                else:
                    args = SimArgs(dem, num_shots_per_thread+remaining_shots,
                                     error_map)
                
                thread_args.append(args)
          
            # Divide simulation trials over the available threads in the system
            with Pool(num_threads) as p:
                sim_data = p.map(sim, thread_args)
                
                # Combine the per-thread distributions into one global distribution
                # 3 options for spacelike error lengths [0, 1, 2], 2 for time [0, 1]
                final_distribution = np.zeros((3,2), dtype=np.uint64)
                final_total = 0
                for i in range(final_distribution.shape[0]):
                    for j in range(final_distribution.shape[1]):
                        final_distribution[i][j] += sum([data[0][i][j] for data in sim_data])
                final_total = sum([data[1] for data in sim_data])

                results = {}

                for i in range(final_distribution.shape[0]):
                    for j in range(final_distribution.shape[1]):
                        results[f"s={i},t={j}"] = 100*(final_distribution[i][j] / final_total)
                        print(f"Spacelike = {i}, Timelike = {j}: {results[f's={i},t={j}']} %")
                print()

                with open(outfile, "w") as f:
                    json.dump(results, f, indent=4)
                

def parse_simulation_args():
    parser = argparse.ArgumentParser()

    # Parse command-line options
    parser.add_argument("-f", "--arg_file", help="Path to JSON file containing simulation arguments.")
    parser.add_argument("-d", "--distances", help="Code distances to simulate", nargs="*")
    parser.add_argument("-e", "--error_rates", help="Physical error rates to simulate", nargs="*")
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
                num_shots = sim_args["num_shots"]
                output_dir = sim_args["output_dir"]
            
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

        if args.distances:
            distances = [int(d) for d in args.distances]

        if args.error_rates:
            error_rates = [float(e) for e in args.error_rates]
        
        if args.num_shots:
            num_shots = args.num_shots
        
        output_dir = "stats/"
        if args.output_dir != None:
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
        
    if output_dir[-1] != "/":
        output_dir += "/"    
    output_dir += f"error_frequency_distribution/"

    return (distances, error_rates, num_shots, output_dir)

def main():
    (distances, error_rates, num_shots, output_dir) = parse_simulation_args()

    run_simulation(distances, error_rates, num_shots, output_dir)

if __name__ == "__main__":
    main()