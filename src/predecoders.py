import numpy as np
from math import sqrt

class Predecoder():
    def __init__(self, distance, batch_size):
        '''
        L1 Predecoder constructor.

        Parameters:
            distance (int): code distance of the surface code to be decoded
            batch_size (int): number of syndrome rounds to be decoded in one batch
        '''
        self.distance = distance
        self.batch_size = batch_size

        # Number of syndrome bits per round
        self.num_syndromes = (self.distance+1)*((self.distance-1)//2)
        # Number of data qubits in the surface code
        self.num_data_qubits = self.distance**2

    def _clear_measurement_errors(self, prev_syndrome, curr_syndrome):
        '''
        Utility function to detect and clear measurement errors
        between consecutive syndrome rounds.

        Parameters:
            prev_syndrome (np.ndarray): older syndrome round
            curr_syndrome (np.ndarray): newer syndrome round

        Returns:
            Nothing, but modifies the syndromes in place by clearing bits!
        '''
        for inx in range(self.num_syndromes):
            # If the same syndrome is active in both rounds, that's
            # indicative of a measurement error. Clear the syndrome
            # in both rounds
            andval = curr_syndrome[inx] & prev_syndrome[inx]
            curr_syndrome[inx] ^= andval
            prev_syndrome[inx] ^= andval
    
    def decode_batch(self, syndrome_batch):
        '''
        Decodes a batch of syndrome rounds to produce corrections and
        determine if the batch was complex.

        Parameters:
            syndrome_batch (np.ndarray): Array of syndrome rounds comprising the
                                         current batch
        
        Returns:
            out (tuple(np.ndarray, bool)): A tuple (batch_corrections, batch_complex) where 
                                           batch_corrections is a flat list of the net corrections
                                           needed to be applied to each data qubit and batch_complex
                                           is a flag inidicating if any of the syndrome rounds within
                                           the predecoded batch was complex.
        '''
        # The supplied syndrome batch has the expected number of rounds
        assert(syndrome_batch.shape[0] == self.batch_size)

        batch_complex = False
        batch_corrections = np.zeros(self.num_data_qubits, dtype=np.uint8)

        # The initial 'previous' round of syndromes can default to 0
        prev_syndrome = np.zeros(syndrome_batch.shape[1], dtype=np.uint8)

        for curr_syndrome in syndrome_batch:
            (corrections, iscomplex) = self.decode(prev_syndrome, curr_syndrome)
            
            # Update complex flag at the batch level
            if iscomplex:
                batch_complex = True

            # Accumulate this round of corrections
            batch_corrections ^= corrections

            prev_syndrome = curr_syndrome

        return (batch_corrections, batch_complex)

    def decode(self, prev_syndrome, curr_syndrome):
        '''
        A function template describing how to predecode a pair
        of successive syndrome rounds. Each specific L1 predecoder must
        implement this function themselves!
        
        Parameters:
            prev_syndrome (np.ndarray): Previous round of syndromes
            curr_syndrome (np.ndarray): Current round of syndromes
        
        Returns:
            out (tuple(np.ndarray, bool)): A tuple (corrections, iscomplex) where corrections is
                                           a flat list of corrections to apply to the data qubits. 
                                           A 1 indicates the data qubit at that position should
                                           be corrected. Indices are specified in row-major order.
                                           iscomplex is a flag indicating if the syndrome was complex 
                                           (i.e., that predecoded corrections should not be used).
        '''
        pass

    def is_logical_error(self, errors, corrections, observable_flip):
        '''
        Checks whether the predecoder's corrections for a given
        shot of a Stim circuit caused a logical error, depending on 
        if the Stim circuit's logical observable flipped during the shot.

        Parameters:
            corrections (np.ndarray): corrections produced by the predecoder
            observable_flip (bool): True if the Stim circuit's logical observable
                                    flipped during the decoded shot, False otherwise
        
        Returns:
            (bool): True if a logical error was introduced, False otherwise
        '''
        pass

class Clique(Predecoder):
    '''
        Clique cryogenic predecoder from arXiv:2208.08547.
    '''
    def __init__(self, distance, batch_size):
        super().__init__(distance, batch_size)

        self.num_syndrome_rows = self.distance+1
        self.num_syndrome_cols = (self.distance - 1) // 2

    def decode(self, prev_syndrome, curr_syndrome):
        """
        Executes Clique's predecoding logic on a pair of successive
        syndrome rounds.

        Parameters:
            prev_syndrome (np.ndarray): Previous round of syndromes
            curr_syndrome (np.ndarray): Current round of syndromes

        Returns:
            out (tuple(np.ndarray, bool)): A tuple (corrections, iscomplex) where corrections is
                                           a flat list of corrections to apply to the data qubits. 
                                           A 1 indicates the data qubit at that position should
                                           be corrected. Indices are specified in row-major order.
                                           iscomplex is a flag indicating if the syndrome was complex 
                                           (i.e., that predecoded corrections should not be used).
        """
        d = self.distance
        num_syndrome_rows = self.num_syndrome_rows
        num_syndrome_cols = self.num_syndrome_cols
        
        corrections = np.zeros(self.num_data_qubits, dtype=np.uint8)

        # Instantiate a decoding clique centered over each ancilla
        for i in range(num_syndrome_rows):
            for j in range(num_syndrome_cols):
                # top right ancilla/data qubits for current clique
                tr_parity_row_index = i - 1
                tr_parity_col_index = j + 1 - i%2
                tr_data_row_index = i - 1
                tr_data_col_index = 2*(j+1) - i%2   
                # bottom right ancilla/data qubits for current clique
                br_parity_row_index = i + 1
                br_parity_col_index = j + 1 - i%2
                br_data_row_index = i
                br_data_col_index = 2*(j+1) - i%2
                # bottom left ancilla/data qubits for current clique
                bl_parity_row_index = i + 1
                bl_parity_col_index = j - i%2   
                bl_data_row_index = i
                bl_data_col_index =  2*(j+1) - i%2 - 1
                # top left ancilla/data qubits for current clique
                tl_parity_row_index = i - 1
                tl_parity_col_index = j - i%2                 
                tl_data_row_index = i - 1
                tl_data_col_index = 2*(j+1) - i%2 - 1

                # Index for center ancilla of the clique
                center_inx = (i*num_syndrome_cols) + j

                # Index for leaf ancillas of the clique
                tr_syn_inx = (tr_parity_row_index*num_syndrome_cols) + tr_parity_col_index
                br_syn_inx = (br_parity_row_index*num_syndrome_cols) + br_parity_col_index
                bl_syn_inx = (bl_parity_row_index*num_syndrome_cols) + bl_parity_col_index
                tl_syn_inx = (tl_parity_row_index*num_syndrome_cols) + tl_parity_col_index

                # Index for data qubits covered by the clique
                tr_data_inx = (tr_data_row_index*d) + tr_data_col_index
                br_data_inx = (br_data_row_index*d) + br_data_col_index
                bl_data_inx = (bl_data_row_index*d) + bl_data_col_index
                tl_data_inx = (tl_data_row_index*d) + tl_data_col_index


                # Extract syndrome values at the center and leaves of the clique
                # The (1 - prev) & curr is used to filter out active syndrome due to measurement errors which
                # are indicated by a pair of 1s on the same ancilla in the two succesive rounds
                center_value = (1-prev_syndrome[center_inx]) & (curr_syndrome[center_inx]) # this is the center

                if 0 <= tr_parity_row_index < num_syndrome_rows and 0 <= tr_parity_col_index < num_syndrome_cols:
                    tr_value = (1-prev_syndrome[tr_syn_inx]) & (curr_syndrome[tr_syn_inx])
                else:
                    tr_value = -1
                if 0 <= br_parity_row_index < num_syndrome_rows and 0 <= br_parity_col_index < num_syndrome_cols:
                    br_value = (1-prev_syndrome[br_syn_inx]) & (curr_syndrome[br_syn_inx])
                else:
                    br_value = -1
                if 0 <= bl_parity_row_index < num_syndrome_rows and 0 <= bl_parity_col_index < num_syndrome_cols:
                    bl_value = (1-prev_syndrome[bl_syn_inx]) & (curr_syndrome[bl_syn_inx])
                else:
                    bl_value = -1
                if 0 <= tl_parity_row_index < num_syndrome_rows and 0 <= tl_parity_col_index < num_syndrome_cols:
                    tl_value = (1-prev_syndrome[tl_syn_inx]) & (curr_syndrome[tl_syn_inx])
                else:
                    tl_value = -1


                # Decode local syndromes using the logic from the paper
                count=0
                iscomplex=0
                if(center_value==1):
                    if(tr_value==1):
                        count+=1
                    if(br_value==1):
                        count+=1
                    if(bl_value==1):
                        count+=1
                    if(tl_value==1):
                        count+=1
                        
                    if(count%2==0): 
                        # First check if this is an edge or corner
                        if((i%2==0 and j==(num_syndrome_cols-1)) or (i%2==1 and j==0)):
                            # This is an edge or corner
                            iscomplex=0
                            # Setting one of two options for edges and a specific one for corner
                            if(i<num_syndrome_rows-1): 
                                row=i
                            else:
                                row=i-1
                            if(j==0):
                                col=0
                            else:
                                col=d-1
                            corrections[(row*d) + col] = 1
                        else:
                            # This is not an edge or corner
                            iscomplex=1
                            return (corrections, iscomplex)
                    else:
                        # Assign the correction
                        if(tr_value==1):
                            corrections[tr_data_inx] = 1
                        if(br_value==1):
                            corrections[br_data_inx] = 1
                        if(bl_value==1):
                            corrections[bl_data_inx] = 1
                        if(tl_value==1):
                            corrections[tl_data_inx] = 1
                        
        return (corrections, iscomplex)

    def is_logical_error(self, errors, corrections, observable_flip):
        '''
        Checks whether the Clique predecoder produced a logical error.
        Normally, to check for logical errors, we just check the corrections to
        see if a logical observable flip was predicted in Stim circuit shots where the observable
        was flipped. This is sufficient because most decoding algorithms (e.g., Pymatching, Pinball)
        either produce a valid set of corrections (i.e., corrections differ from errors by at most a
        product of stabilizers) or the set of corrections flips the logical observable.
        
        However, due to the way that Clique handles measurement errors, it can produce a set of
        corrections which is neither valid nor flips the logical observable, so if we only check
        the logical observable to verify correctness, there will be some false positives. Therefore,
        to fully verify Clique's corrections, we need to do some more rigorous checking here.

        Parameters:
            corrections (np.ndarray): net result of data errors and generated corrections
            observable_flip (bool): whether or not the logical observable was flipped in 
                                    the decoded Stim circuit shot

        Returns:
            (int): 2, if decoder corrections were invalid (uncleared syndromes left)
                1, if decoder corrections produced a logical error
                0, otherwise
        '''
        # Dimension, d, of the corrections array
        d = int(sqrt(len(corrections)))
        # XOR corrections with errors to get net operations on qubits
        result = corrections ^ np.bitwise_xor.reduce(errors)

        def _all_syndromes_clear():
            '''
            Check that all syndromes would have been cleared by the supplied corrections

            Returns:
                (bool): True if all syndromes have been cleared, False otherwise
            '''
            # Iterate over rows and columns of ancillas
            for row in range(d+1):
                for col in range((d-1)//2):
                    # Even-indexed row
                    if (row % 2) == 0:
                        top_left = d*(row-1) + 1 + 2*col
                        top_right = top_left + 1
                        bottom_left = d*row + 1 + 2*col
                        bottom_right = bottom_left + 1
                    # Odd-indexed row
                    else:
                        top_left = d*(row-1) + 2*col
                        top_right = top_left + 1
                        bottom_left = d*row + 2*col
                        bottom_right = bottom_left + 1

                    parity = 0
                    if top_left >= 0:
                        parity ^= result[top_left]
                    if top_right >= 0:
                        parity ^= result[top_right]
                    if bottom_left < d*d:
                        parity ^= result[bottom_left]
                    if bottom_right < d*d:
                        parity ^= result[bottom_right]
                    
                    # This ancilla would not have been cleared,
                    # return early
                    if (parity):
                        return False
            
            # All ancillas passed
            return True

        def _is_logical_error():
            '''
            Check whether the generated corrections form a logical error

            Returns:
                (int): True if a logical error has been formed, False otherwise
            '''
            # Form a 2d array to iterate over the rows        
            data = np.reshape(result, (d, d))

            # We're decoding Z errors so we need to go over the columns of
            # the data qubit array
            transpose = np.transpose(data).tolist()

            # If any row has an odd number of corrections in it,
            # we've formed a logical error
            for row in transpose:
                if row.count(1) % 2:
                    return True
                
            return False

        # == CHECKING VALIDITY OF CORRECTIONS ==
        
        # First, we will check that all syndromes are cleared
        # (i.e., the corrections have formed some kind of loop(s))
        if not _all_syndromes_clear() or _is_logical_error():
            return True # indicate decoding error
        
        # If we've gotten this far, the corrections successfully formed
        # a stabilizer or a product of stabilizers
        return False
    
class Pinball(Predecoder):
    '''
    Pinball cryogenic predecoder tailored to circuit-level noise.
    '''
    def __init__(self, distance, batch_size):
        super().__init__(distance, batch_size)

        # Dimensions of the per-round syndrome bits arrayz
        self.num_syndrome_rows = self.distance+1
        self.num_syndrome_cols = (self.distance - 1) // 2

    def _clear_bulk_data_errors(self, syndrome, corrections):
        '''
        Utility function to predecode space-like data errors within
        the bulk of the surface code decoding graph.

        Parameters:
            syndrome (np.ndarray): the list of syndrome bits for a given syndrome round
            corrections (np.ndarray): the list of corrections to modify based on the
                                      list of syndrome bits
        
        Returns:
            Nothing, but the corrections array is updated in place with the predecoding
            results!
        '''
        # 4 pipeline stages to handle data errors
        for trial in range(4):
            # Iterate over all ancillas and see if a leaf decoder
            # should be instantiated over them
            for i in range(self.num_syndrome_rows):
                for j in range(self.num_syndrome_cols):
                    if(i%2==0): #only tackle odd rows
                        continue

                    if(trial==0):
                        # top right
                        parity_row_index = i - 1
                        parity_col_index = j + 1 - i%2
                        data_row_index = i - 1
                        data_col_index = 2*(j+1) - i%2   
                    elif(trial==1):
                        # bottom right
                        parity_row_index = i + 1
                        parity_col_index = j + 1 - i%2
                        data_row_index = i
                        data_col_index = 2*(j+1) - i%2
                    elif(trial==2):
                        # bottom left
                        parity_row_index = i + 1
                        parity_col_index = j - i%2   
                        data_row_index = i
                        data_col_index =  2*(j+1) - i%2 - 1
                    else:
                        # top left
                        parity_row_index = i - 1
                        parity_col_index = j - i%2                 
                        data_row_index = i - 1
                        data_col_index = 2*(j+1) - i%2 - 1

                    # Calculate the index of the center/neighbor ancillas in the leaf decoder as well
                    # as the index of the data qubit between them
                    center_inx = (i*self.num_syndrome_cols) + j
                    neighbor_inx = (parity_row_index * self.num_syndrome_cols) + parity_col_index
                    data_inx = (data_row_index * self.distance) + data_col_index

                    value1 = syndrome[center_inx] # this has to exist

                    # We defer decoding data errors at the edge of the lattice to the last step
                    # such that we can greedily consume two syndromes as often as possible. So, fix
                    # the neighbor ancilla value to 0 here if the neighbor doesn't exist and deal with it later
                    if 0 <= parity_row_index < self.num_syndrome_rows and \
                       0 <= parity_col_index < self.num_syndrome_cols:
                        value2 = syndrome[neighbor_inx]
                    else:
                        value2 = 0 #due to clockwise this is okay

                    if(0 <= data_row_index < self.distance and 0 <= data_col_index < self.distance and value2 != 0):
                        # The data qubit and neighbor ancilla for this leaf decoder exist. If both syndromes are
                        # active, apply the correction to the data qubit and clear both syndrome bits
                        andval = value1 & value2
                        corrections[data_inx] ^= andval
                        syndrome[center_inx] ^= andval
                        syndrome[neighbor_inx] ^= andval

    def _clear_edge_data_errors(self, syndrome, corrections):
        '''
        Utility function to predecode space-like data errors at
        the edge of the surface code decoding graph.

        Parameters:
            syndrome (np.ndarray): the list of syndrome bits for a given syndrome round
            corrections (np.ndarray): the list of corrections to modify based on the
                                      list of syndrome bits
        
        Returns:
            Nothing, but the corrections array is updated in place with the predecoding
            results!
        '''
        # Leftmost column of data qubits
        for i in range(self.num_syndrome_rows):
            if (i%2==0):
                continue
            j = 0

            center_inx = i*self.num_syndrome_cols + j

            value1 = syndrome[center_inx]
            if(value1):
                # Always correct the top left data qubit (doesn't actually matter which you choose)
                data_col_index = 0
                data_row_index = i-1
                corrections[(data_row_index*self.distance) + data_col_index] ^= 1
                syndrome[center_inx] ^= 1

        # Rightmost column of data qubits
        for i in range(self.num_syndrome_rows): 
            if(i%2==1): # only for even rows
                continue
            j = self.num_syndrome_cols - 1

            center_inx = i*self.num_syndrome_cols + j

            value1 = syndrome[center_inx]
            if(value1):
                # Always correct the bottom right data qubit (doesn't actually matter which you choose)
                data_col_index = self.distance-1
                data_row_index = i
                corrections[(data_row_index*self.distance) + data_col_index] ^= 1
                syndrome[center_inx] ^= 1
    
    def _clear_spacetime_errors(self, prev_syndrome, curr_syndrome, corrections):
        '''
        Utility function to predecode the two types of single-qubit spacetime-like
        errors present in the surface code decoding graph.

        Parameters:
            prev_syndrome (np.ndarray): the list of syndrome bits for the previous syndrome round
            curr_syndrome (np.ndarray): the list of syndrome bits for the current syndrome round
            corrections (np.ndarray): the list of corrections to modify based on the syndrome bits
        
        Returns:
            Nothing, but the corrections array is updated in place with the predecoding
            results!
        '''
        # Spacetime checks (top right, top left)
        for trial in range(2):
            for i in range(self.num_syndrome_rows):
                for j in range(self.num_syndrome_cols):
                    if trial == 0:
                        # top right
                        parity_row_index = i - 1
                        parity_col_index = j + 1 - i%2
                        data_row_index = i - 1
                        data_col_index = 2*(j+1) - i%2
                    else:
                        # top left
                        parity_row_index = i - 1
                        parity_col_index = j - i%2                 
                        data_row_index = i - 1
                        data_col_index = 2*(j+1) - i%2 - 1

                    # For the syndrome bit currently being processed, calculates its index,
                    # the index of its neighbor syndrome, and the index of the data qubit on
                    # the edge between them
                    center_inx = (i*self.num_syndrome_cols) + j
                    neighbor_inx = (parity_row_index * self.num_syndrome_cols) + parity_col_index
                    data_inx = (data_row_index * self.distance) + data_col_index

                    value1 = curr_syndrome[center_inx] # this has to exist
                    if 0 <= parity_row_index < self.num_syndrome_rows and 0 <= parity_col_index < self.num_syndrome_cols:
                        value2 = prev_syndrome[neighbor_inx]
                    else:
                        value2 = 0 #due to clockwise this is okay
                    
                    if(0 <= data_row_index < self.distance and 0 <= data_col_index < self.distance and value2 != -1):
                        # The data qubit and neighbor ancilla for this leaf decoder exist. If both syndromes are
                        # active, apply the correction to the data qubit and clear both syndrome bits
                        andval = value1 & value2
                        corrections[data_inx] ^= andval
                        curr_syndrome[center_inx] ^= andval
                        prev_syndrome[neighbor_inx] ^= andval

    def _clear_hook_errors(self, prev_syndrome, curr_syndrome, corrections):
        '''
        Utility function to predecode the hook errors (two-qubit spacetime-like
        errors) present in the surface code decoding graph.

        Parameters:
            prev_syndrome (np.ndarray): the list of syndrome bits for the previous syndrome round
            curr_syndrome (np.ndarray): the list of syndrome bits for the current syndrome round
            corrections (np.ndarray): the list of corrections to modify based on the syndrome bits
        
        Returns:
            Nothing, but the corrections array is updated in place with the predecoding
            results!
        '''
        # Check for possible hook errors at each syndrome in the decoding graph
        for i in range(2, self.num_syndrome_rows):
            for j in range(self.num_syndrome_cols):
                curr_val = curr_syndrome[i*self.num_syndrome_cols + j]
                prev_val = prev_syndrome[(i-2)*self.num_syndrome_cols + j]
                andval = curr_val & prev_val
                
                # If both active, clear the syndromes associated with the hook error
                curr_syndrome[i*self.num_syndrome_cols + j] ^= andval
                prev_syndrome[(i-2)*self.num_syndrome_cols + j] ^= andval

                # Assign correction to the pair of data qubits
                col = 2*(j+1) - i%2 - 1
                corrections[(i-1)*self.distance + col] ^= andval
                corrections[(i-2)*self.distance + col] ^= andval

    def decode_batch(self, syndrome_batch):
        batch_corrections, _ = super().decode_batch(syndrome_batch)
        
        # In addition to normal predecoding over the syndrome batch, we must
        # also clear edge errors in the final syndrome round
        self._clear_edge_data_errors(syndrome_batch[-1], batch_corrections)
        
        # Only check for complex once we're done processing
        # the whole batch
        batch_complex = np.any(syndrome_batch)

        return batch_corrections, batch_complex
    
    def decode(self, prev_syndrome, curr_syndrome):
        """
        Executes Pinball's predecoding logic over a pair of successive
        rounds of syndromes. Executes predecoding primitives for each type
        of error in the order specified in the paper.

        Parameters:
            prev_syndrome (np.ndarray): Previous round of syndromes
            curr_syndrome (np.ndarray): Current round of syndromes

        Returns:
            out (tuple(np.ndarray, bool)): A tuple (corrections, iscomplex) where corrections is
                                           a flat list of corrections to apply to the data qubits. 
                                           A 1 indicates the data qubit at that position should
                                           be corrected. Indices are specified in row-major order.
                                           iscomplex is a flag indicating if the syndrome was complex 
                                           (i.e., that predecoded corrections should not be used).
        """
        corrections = np.zeros(self.distance*self.distance, dtype=np.uint8)

        self._clear_measurement_errors(prev_syndrome, curr_syndrome)
        
        self._clear_bulk_data_errors(curr_syndrome, corrections)
        
        self._clear_spacetime_errors(prev_syndrome, curr_syndrome, corrections)   

        self._clear_hook_errors(prev_syndrome, curr_syndrome, corrections)

        self._clear_edge_data_errors(prev_syndrome, corrections)

        # Check round-by-round complex doesn't make sense here, so always set to 0
        iscomplex = 0
        
        return (corrections, iscomplex)

    def is_logical_error(self, errors, corrections, observable_flip):
        # Stim circuit's X-basis logical observable is the leftmost column of data qubits
        prediction = np.bitwise_xor.reduce(
                        corrections[[i*self.distance for i in range(self.distance)]])
    
        return prediction != observable_flip
