import argparse
import numpy as np
import pickle
from collections import defaultdict, deque

from os import makedirs, cpu_count, path
import sys
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '../')))

from multiprocessing import Pool
from math import floor
import json

import stim

from src import utils

def get_max_length_error_chain(
        error_shot: list[int],
        error_map: dict[int, list[tuple[int,int,int]]]) -> int:
    '''
    Returns the maximum length error chain observed in a shot of a
    Stim circuit. Here, length is measured as the number of edges in the
    error detector model rather than the number of adjacent data qubits that
    had an error. For example, a hook error features errors on two adjacent
    data qubits, but it is represented by a single edge in the detector error
    model, so it would still be a length-1 error chain.

    Parameters:
        error_shot: list of error IDs sampled from the Stim circuit
        error_map: mapping from error IDs to the detectors in the Stim
                   circuit that they flip

    Returns:
        the length of the longest error chain
    '''

    def combine_errors(errors):
        # Build adjacency list
        adj = defaultdict(set)
        for p1, p2 in errors:
            dist = 1
            adj[p1].add((p2,dist))
            adj[p2].add((p1,dist))

        visited = set()
        def bfs(start):
            queue = deque([start])
            local_visited = set()
            path = []
            total_distance = 0
            while queue:
                point = queue.popleft()
                if point in visited:
                    continue

                visited.add(point)
                local_visited.add(point)
                path.append(point)

                for neighbor, dist in adj[point]:
                    if neighbor not in visited:
                        total_distance += dist
                        queue.append(neighbor)
            return path, total_distance

        # Form chains from the errors
        chains = []
        for point in adj:
            if point not in visited:
                chain, total_distance = bfs(point)
                if len(chain) > 1:
                    chains.append((chain, total_distance))

        return chains
    
    # Form all chains from the errors in the shot, and find the
    # max length chain
    error_mechanisms = []
    for error in error_shot:
        try:
            # Get endpoints of error mechanism
            detector_coords = error_map[error]
            error_mechanisms.append(detector_coords)
        except:
            continue

    # Combine any error mechanisms that share a detector into
    # longer chains
    chains = combine_errors(error_mechanisms)

    # Record the maximum length error chain occurring in this shot
    if len(chains) > 0:
        return max([len(chain[0]) - 1 for chain in chains])
    else:
        return 0

class SimArgs():
    def __init__(self, dem, num_shots, error_map):
        self.dem: stim.DetectorErrorModel = dem
        self.num_shots: int = num_shots
        self.error_map: dict = error_map

def sim(args: SimArgs):
    sampler = args.dem.compile_sampler()
    longest_chain_per_shot = []

    for _ in range(args.num_shots):
        _, _, error_shot = sampler.sample(shots=1, return_errors=True)

        # Collect maximum length error chain for the shot
        max_length_chain = get_max_length_error_chain(np.flatnonzero(error_shot), args.error_map)
        longest_chain_per_shot.append(max_length_chain)
        

    # Record distribution of max length chains
    longest_chain = max(longest_chain_per_shot)
    distribution = np.zeros(longest_chain+1, dtype=np.uint64)
    for length in longest_chain_per_shot:
        distribution[length] += 1

    return distribution

def run_simulation(distances, error_rates, num_shots, output_dir):
    for i, d in enumerate(distances):
        # Make sure the simulation output directory exists
        dirname = output_dir + f"d={d}/"
        makedirs(dirname, exist_ok=True)
        
        fname = f"../metadata/d={d}/errors_to_detectors.pkl"
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
                longest_chain = max(len(data) for data in sim_data)
                final_distribution = np.zeros(longest_chain+1, dtype=np.uint64)
                for data in sim_data:
                    for i in range(final_distribution.shape[0]):
                        if i < len(data):
                            final_distribution[i] += data[i]
                        else:
                            break

                results = {}
                for i in range(final_distribution.shape[0]):
                    results[str(i)] = 100*(final_distribution[i] / num_shots)
                    print(f"Chain length = {i}: {results[str(i)]}")
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
    output_dir += f"chain_length_distribution/"

    return (distances, error_rates, num_shots, output_dir)

def main():
    (distances, error_rates, num_shots, output_dir) = parse_simulation_args()

    run_simulation(distances, error_rates, num_shots, output_dir)

if __name__ == "__main__":
    main()