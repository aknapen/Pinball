module pinball #(
    parameter CODE_DISTANCE = `CODE_DISTANCE,
    parameter NUM_ROWS = CODE_DISTANCE+1,
    parameter NUM_COLS = (CODE_DISTANCE-1) / 2
) (
    input clk,
    input rstn,
    input[NUM_ROWS-1:0][NUM_COLS-1:0] syndrome_in,
    input                             valid_in,

    output valid_out,
    output complex_out,
    output[CODE_DISTANCE-1:0][CODE_DISTANCE-1:0] corrections_out
);
    localparam COUNT_WIDTH = $clog2(CODE_DISTANCE);

    // Clock-gated inputs
    logic[NUM_ROWS-1:0][NUM_COLS-1:0] curr_syndrome_array;
    logic curr_syndrome_array_vld;

    // Stored syndrome from the previous round
    logic[NUM_ROWS-1:0][NUM_COLS-1:0] prev_syndrome_array;

    // Syndrome results at each pipeline stage for the CURRENT syndrome
    logic[NUM_ROWS-1:0][NUM_COLS-1:0] res1_curr, res2_curr, res3_curr, res4_curr,
                                      res5_curr, res6_curr, res7_curr, res8_curr;
    // Syndrome results at relevant pipeline stages for the PREVIOUS syndrome
    logic[NUM_ROWS-1:0][NUM_COLS-1:0] res1_prev, res5_prev, res6_prev, res7_prev, 
                                      res8_prev, res9_prev;

    // Syndrome registers between pipeline stages for the CURRENT syndrome
    logic[NUM_ROWS-1:0][NUM_COLS-1:0] st1_2_curr, st2_3_curr, st3_4_curr, st4_5_curr,
                                      st5_6_curr, st6_7_curr, st7_8_curr, st8_9_curr;
    // Syndrome registers between relevant pipeline stages for the PREVIOUS syndrome
    logic[NUM_ROWS-1:0][NUM_COLS-1:0] st0_prev, st5_6_prev, st6_7_prev, st7_8_prev,
                                      st8_9_prev;

    // Holds the corrections round for each pipeline stage
    logic[CODE_DISTANCE-1:0][CODE_DISTANCE-1:0] st1_corr, st2_corr, st3_corr, st4_corr,
                                                st5_corr, st6_corr, st7_corr, st8_corr,
                                                st9_corr, final_corr;
    // Correction registers between pipeline stages
    logic[CODE_DISTANCE-1:0][CODE_DISTANCE-1:0] st1_2_corr, st2_3_corr, st3_4_corr, st4_5_corr,
                                                st5_6_corr, st6_7_corr, st7_8_corr, st8_9_corr;

    // Stage valid signals
    logic st1_2_vld, st2_3_vld, st3_4_vld, st4_5_vld, st5_6_vld, st6_7_vld, st7_8_vld, st8_9_vld;

    // Count which of the D+1 rounds is being entered into the pipeline
    logic[COUNT_WIDTH-1:0] round_counter;

    // D-round block level outputs
    logic blk_vld, blk_complex;
    logic[CODE_DISTANCE-1:0][CODE_DISTANCE-1:0] blk_corr;

    // Valid signal registers
    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            curr_syndrome_array_vld <= 0;

            st1_2_vld <= 0;
            st2_3_vld <= 0;
            st3_4_vld <= 0;
            st4_5_vld <= 0;
            st5_6_vld <= 0;
            st6_7_vld <= 0;
            st7_8_vld <= 0;
            st8_9_vld <= 0;

            blk_vld <= 0;
        end
        else begin
            if (valid_in) begin
                curr_syndrome_array_vld <= 1;
            end
            else begin
                curr_syndrome_array_vld <= 0;

                st1_2_vld <= curr_syndrome_array_vld;
                st2_3_vld <= st1_2_vld;
                st3_4_vld <= st2_3_vld;
                st4_5_vld <= st3_4_vld;
                st5_6_vld <= st4_5_vld;
                st6_7_vld <= st5_6_vld;
                st7_8_vld <= st6_7_vld;
                st8_9_vld <= st7_8_vld;

                blk_vld <= st8_9_vld & (round_counter == CODE_DISTANCE);
            end
        end
    end

    // Current syndrome registers
    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            curr_syndrome_array <= '0;
            prev_syndrome_array <= '0;

            st1_2_curr <= '0;
            st2_3_curr <= '0;
            st3_4_curr <= '0;
            st4_5_curr <= '0;
            st5_6_curr <= '0;
            st6_7_curr <= '0;
            st7_8_curr <= '0;
            st8_9_curr <= '0;
        end
        // Propagate updated syndromes to next pipeline stage
        else begin
            if (valid_in)
                curr_syndrome_array <= syndrome_in;
                prev_syndrome_array <= st0_prev;
            else
                curr_syndrome_array <= '0;
                prev_syndrome_array <= '0;
            
            if(curr_syndrome_array_vld)
                st1_2_curr <= res1_curr;
            if(st1_2_vld)
                st2_3_curr <= res2_curr;
            if(st2_3_vld)
                st3_4_curr <= res3_curr;
            if(st3_4_vld)
                st4_5_curr <= res4_curr;
            if(st4_5_vld)
                st5_6_curr <= res5_curr;
            if(st5_6_vld)
                st6_7_curr <= res6_curr;
            if(st6_7_vld)
                st7_8_curr <= res7_curr;
            if(st7_8_vld)
                st8_9_curr <= res8_curr;
        end
    end

    // Previous syndrome registers
    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            st5_6_prev <= '0;
            st6_7_prev <= '0;
            st7_8_prev <= '0;
            st8_9_prev <= '0;

            st0_prev <= '0;
        end
        // Propagate updated syndromes to next pipeline stage
        else begin
            if(st4_5_vld)
                st5_6_prev <= res1_prev;
            if(st5_6_vld)
                st6_7_prev <= res6_prev;
            if(st6_7_vld)
                st7_8_prev <= res7_prev;
            if(st7_8_vld)
                st8_9_prev <= res8_prev;
            // Set prev_syndrome_array for next syndrome round
            if(blk_vld)
                prev_syndrome_array <= 0;
            else if(st8_9_vld)
                st0_prev <= st8_9_curr;
        end
    end

    // Correction registers
    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            st1_2_corr <= '0;
            st2_3_corr <= '0;
            st3_4_corr <= '0;
            st4_5_corr <= '0;
            st5_6_corr <= '0;
            st6_7_corr <= '0;
            st7_8_corr <= '0;
            st8_9_corr <= '0;
        end
        // Propagate cumulative corrections to next pipeline stage
        else begin
            if(curr_syndrome_array_vld)
                st1_2_corr <= st1_corr;
            if(st1_2_vld)
                st2_3_corr <= st1_2_corr ^ st2_corr;
            if(st2_3_vld)
                st3_4_corr <= st2_3_corr ^ st3_corr;
            if(st3_4_vld)
                st4_5_corr <= st3_4_corr ^ st4_corr;
            if(st4_5_vld)
                st5_6_corr <= st4_5_corr ^ st5_corr;
            if(st5_6_vld)
                st6_7_corr <= st5_6_corr ^ st6_corr;
            if(st6_7_vld)
                st7_8_corr <= st6_7_corr ^ st7_corr;
            if(st7_8_vld)
                st8_9_corr <= st7_8_corr ^ st8_corr;
        end
    end

    // Round counter register
    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            round_counter <= '0;
        end
        else begin
            // Increment wrapping round_counter once the current
            // round has finished going through the pipeline
            if (st8_9_vld) begin
                if (round_counter == CODE_DISTANCE) begin
                    round_counter <= '0;
                end
                else begin
                    round_counter <= round_counter + 1;
                end
            end
        end
    end

    // Block complex register
    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            blk_complex <= '0;
        end
        else begin
            // Reset block complex when the next round comes in
            if (valid_in) begin
                blk_complex <= 0;
            end
            else if (st8_9_vld) begin
                blk_complex <= (|(res9_prev)) | blk_complex;
            end
        end
    end

    // Block correction register
    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            blk_corr <= '0;
        end
        else begin
            // Reset block corrections when the next round comes in
            if (blk_vld) begin
                blk_corr <= '0;
            end
            if (st8_9_vld) begin
                // In the last round, include the edge data corrections for the current
                // syndrome
                if (round_counter == CODE_DISTANCE) begin
                    blk_corr <= ((st9_corr ^ st8_9_corr) ^ blk_corr) ^ final_corr;
                end
                else begin
                    blk_corr <= (st9_corr ^ st8_9_corr) ^ blk_corr;
                end
            end
        end
    end

    generate;
        genvar i,j;

        /////////////////////////////////////////////
        // Stage 1 Logic: Measurement error checks //
        /////////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin
            for (j = 0; j < CODE_DISTANCE; j++) begin
                // Measurement error checks don't touch any
                // data qubits
                assign st1_corr[i][j] = '0;
            end
        end

        for (i = 0; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                // Check for measurement errors between all syndromes
                // from this round and from the previous round
                assign res1_curr[i][j] = curr_syndrome_array[i][j] & ~prev_syndrome_array[i][j];
                assign res1_prev[i][j] = prev_syndrome_array[i][j] & ~curr_syndrome_array[i][j];
            end
        end

        /////////////////////////////////////////////////////
        // Stage 2 Logic: Top right bulk data error checks //
        /////////////////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin : st1_corr_row
            for (j = 0; j < CODE_DISTANCE; j++) begin : st1_corr_col
                // Data qubits in odd rows, or in even columns of
                // even rows, won't be corrected in this stage
                if ((i % 2) || ((j % 2) == 0)) begin
                    assign st2_corr[i][j] = '0;
                end
            end
        end

        for (i = 1; i < NUM_ROWS; i+=2) begin : st1_syn_row
            for (j = 0; j < NUM_COLS; j++) begin : st1_syn_col
                // Decode from odd rows of ancillas
                leaf_decode dec(.center_in(st1_2_curr[i][j]), 
                                .neighbor_in(st1_2_curr[i-1][j]), 
                                .correction(st2_corr[i-1][2*j + 1]),
                                .center_out(res2_curr[i][j]),
                                .neighbor_out(res2_curr[i-1][j]));
            end
        end
    

        ////////////////////////////////////////////////////////
        // Stage 3 Logic: Bottom right bulk data error checks //
        ////////////////////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin : st2_corr_row
            for (j = 0; j < CODE_DISTANCE; j++) begin : st2_corr_col
                // Data qubits in even rows, or in even columns of
                // odd rows, won't be corrected in this stage
                if (((i % 2) == 0) || ((j % 2) == 0)) begin
                    assign st3_corr[i][j] = '0;
                end
            end
        end

        for (i = 0; i < NUM_ROWS; i++) begin : st2_syn_row
            for (j = 0; j < NUM_COLS; j++) begin : st2_syn_col
                // Top and bottom row ancilla bits are not touched in this stage,
                // so just pass them through
                if ((i == 0) || (i == NUM_ROWS-1)) begin
                    assign res2_curr[i][j] = st2_3_curr[i][j];
                end

                // Only instantiate leaf decoders on odd rows
                else if (i % 2) begin
                    leaf_decode dec(.center_in(st2_3_curr[i][j]), 
                                .neighbor_in(st2_3_curr[i+1][j]), 
                                .correction(st3_corr[i][2*j + 1]),
                                .center_out(res3_curr[i][j]),
                                .neighbor_out(res3_curr[i+1][j]));
                end
            end
        end

        ///////////////////////////////////////////////////////
        // Stage 4 Logic: Bottom left bulk data error checks //
        ///////////////////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin : st3_corr_row
            for (j = 0; j < CODE_DISTANCE; j++) begin : st3_corr_col
                // Data qubits in first, last, and odd columns, as well as
                // data qubits in even rows, won't be corrected in this stage
                if ((j == 0) || (j == CODE_DISTANCE - 1) || (j % 2 == 1) || 
                    (i % 2 == 0)) begin
                    assign st4_corr[i][j] = '0;
                end
            end
        end

        for (i = 0; i < NUM_ROWS; i++) begin : st3_syn_row
            for (j = 0; j < NUM_COLS; j++) begin : st3_syn_col
                /* Syndromes to pass through in this stage:
                    1) First row
                    2) Last row
                    3) First column of odd rows
                    4) Last column of even rows
                */
                if ((i == 0) || (i == NUM_ROWS-1) || 
                    ((j == 0) && (i % 2 == 1)) || 
                    ((j == NUM_COLS-1) && (i % 2 == 0))) begin
                    assign res4_curr[i][j] = st3_4_curr[i][j];
                end

                // Only instantiate leaf decoders on odd rows
                else if (i % 2) begin
                    
                    leaf_decode dec(.center_in(st3_4_curr[i][j]), 
                                    .neighbor_in(st3_4_curr[i+1][j-1]), 
                                    .correction(st4_corr[i][2*j]),
                                    .center_out(res4_curr[i][j]),
                                    .neighbor_out(res4_curr[i+1][j-1]));
                end
            end
        end
    
        ////////////////////////////////////////////////////
        // Stage 5 Logic: Top left bulk data error checks //
        ////////////////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin : st4_corr_row
            for (j = 0; j < CODE_DISTANCE; j++) begin : st4_corr_col
                /* Data qubits untouched in this stage
                    1) First column
                    2) Last column
                    3) Odd columns
                    4) Odd rows
                */
                if ((j == 0) || (j == CODE_DISTANCE-1) || (j % 2 == 1) || (i % 2) == 1) begin
                    assign st5_corr[i][j] = '0;
                end
            end
        end

        for (i = 0; i < NUM_ROWS; i++) begin : st4_syn_row
            for (j = 0; j < NUM_COLS; j++) begin : st4_syn_col
                /* Syndromes to pass through in this stage:
                    1) First column in odd rows
                    2) Last column in even rows
                */
                if (((i % 2 == 1) && (j == 0)) || 
                    ((i % 2 == 0) && (j == NUM_COLS-1))) begin
                    assign res5_curr[i][j] = st4_5_curr[i][j];
                end

                // Instantiate leaf decoders in the odd rows
                else if (i % 2) begin
                    leaf_decode dec(.center_in(st4_5_curr[i][j]), 
                                    .neighbor_in(st4_5_curr[i-1][j-1]), 
                                    .correction(st5_corr[i-1][2*j]),
                                    .center_out(res5_curr[i][j]),
                                    .neighbor_out(res5_curr[i-1][j-1]));
                end
            end
        end

        /////////////////////////////////////////////////////
        // Stage 6 Logic: Top right spacetime error checks //
        /////////////////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin
            for (j = 0; j < CODE_DISTANCE; j++) begin
                /* Data qubits untouched in this stage
                    1) First column
                    2) Last column
                    3) Even columns in even rows
                    4) Odd columns in odd rows
                */
                if ((j == 0) || (j == CODE_DISTANCE-1) ||
                    ((i % 2 == 0) && (j % 2 == 0)) ||
                    ((i % 2 == 1) && (j % 2 == 1))) begin
                    assign st6_corr[i][j] = '0;
                end
            end
        end
            
        for (i = 0; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                /* Ancillas in previous syndrome to pass through in this stage
                  (those which don't have a bottom left neighbor)
                    1) Last row
                    2) First column of odd rows
                */
                if ((i == NUM_ROWS-1) || ((i % 2 == 1) && (j == 0))) begin
                    assign res6_prev[i][j] = st5_6_prev[i][j];
                end

                /* Ancillas in current syndrome to pass through in this stage
                  (those which don't have a top right neighbor)
                    1) First row
                    2) Last column of even rows
                */
                if ((i == 0) || ((i % 2 == 0) && (j == NUM_COLS-1))) begin
                    assign res6_curr[i][j] = st5_6_curr[i][j];
                end                
            end
        end

        for (i = 1; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                // Instantiate leaf decoders from ancillas in the current syndrome to their
                // top right neighbors in the previous syndrome
                if (~((j == NUM_COLS-1) && (i % 2 == 0))) begin
                    leaf_decode dec(.center_in(st5_6_curr[i][j]), 
                                    .neighbor_in(st5_6_prev[i-1][j+1-(i % 2)]),
                                    .correction(st6_corr[i-1][2*(j+1) - (i % 2)]),
                                    .center_out(res6_curr[i][j]),
                                    .neighbor_out(res6_prev[i-1][j+1-(i%2)]));
                end
            end
        end

        ////////////////////////////////////////////////////
        // Stage 7 Logic: Top left spacetime error checks //
        ////////////////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin
            for (j = 0; j < CODE_DISTANCE; j++) begin
                /* Data qubits untouched in this stage
                    1) First column
                    2) Last column
                    3) Even columns in odd rows
                    4) Odd columns in even rows
                */
                if ((j == 0) || (j == CODE_DISTANCE-1) ||
                    ((i % 2 == 0) && (j % 2 == 1)) ||
                    ((i % 2 == 1) && (j % 2 == 0))) begin
                    assign st7_corr[i][j] = '0;
                end
            end
        end
            
        for (i = 0; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                /* Ancillas in previous syndrome to pass through in this stage
                  (those which don't have a bottom right neighbor)
                    1) Last row
                    2) Last column of even rows
                */
                if ((i == NUM_ROWS-1) || ((i % 2 == 0) && (j == NUM_COLS-1))) begin
                    assign res7_prev[i][j] = st6_7_prev[i][j];
                end

                /* Ancillas in current syndrome to pass through in this stage
                  (those which don't have a top left neighbor)
                    1) First row
                    2) First column of odd rows
                */
                if ((i == 0) || ((i % 2 == 1) && (j == 0))) begin
                    assign res7_curr[i][j] = st6_7_curr[i][j];
                end                
            end
        end

        for (i = 1; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                // Instantiate leaf decoders from ancillas in the current syndrome to their
                // top left neighbors in the previous syndrome
                if (~((j == 0) && (i % 2 == 1))) begin
                    leaf_decode dec(.center_in(st6_7_curr[i][j]), 
                                    .neighbor_in(st6_7_prev[i-1][j - (i%2)]),
                                    .correction(st7_corr[i-1][2*(j+1) - (i%2) - 1]),
                                    .center_out(res7_curr[i][j]),
                                    .neighbor_out(res7_prev[i-1][j - (i%2)]));
                end
            end
        end

        //////////////////////////////////////
        // Stage 8 Logic: Hook error checks //
        //////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin
            for (j = 0; j < CODE_DISTANCE; j++) begin
                /* Data qubits untouched in this stage
                    1) Last column
                    2) Even columns in first row
                    3) Odd columns in last row
                */
                if ((j == CODE_DISTANCE-1) ||
                    ((i == 0) && (j % 2 == 0)) ||
                    ((i == CODE_DISTANCE-1) && (j % 2 == 1))) begin
                    assign st8_corr[i][j] = '0;
                end
            end
        end

        for (i = 0; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                /* Ancillas in previous syndrome to pass through in this stage
                  (those which don't have a direct south neighbor)
                    1) Last two rows
                */
                if ((i >= NUM_ROWS-2)) begin
                    assign res8_prev[i][j] = st7_8_prev[i][j];
                end

                /* Ancillas in current syndrome to pass through in this stage
                  (those which don't have a direct north neighbor)
                    1) First two rows
                    2) First column of odd rows
                */
                if ((i < 2)) begin
                    assign res8_curr[i][j] = st7_8_curr[i][j];
                end                
            end
        end

        for (i = 2; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                leaf_decode #(.NUM_CORR_BITS(2)) 
                        dec (.center_in(st7_8_curr[i][j]),
                             .neighbor_in(st7_8_prev[i-2][j]),
                             .correction({st8_corr[i-1][2*(j+1) - (i%2) - 1],
                                          st8_corr[i-2][2*(j+1) - (i%2) - 1]}),
                             .center_out(res8_curr[i][j]),
                             .neighbor_out(res8_prev[i-2][j]));
            end
        end

        ///////////////////////////////////////////
        // Stage 9 Logic: Edge data error checks //
        ///////////////////////////////////////////
        for (i = 0; i < CODE_DISTANCE; i++) begin
            for (j = 0; j < CODE_DISTANCE; j++) begin
                /* Data qubits untouched in this stage
                    1) Non-first or last columns
                    2) Odd rows in first column
                    3) Odd rows in last column
                */
                if (((j > 0) && (j < CODE_DISTANCE-1)) ||
                    (i % 2 == 1)) begin
                    assign st9_corr[i][j] = '0;
                end
            end
        end

        for (i = 0; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                /* Ancillas in previous syndrome to pass through in this stage
                    1) Non-last column in even rows
                    2) Non-first column in odd rows
                */
                if (((i % 2 == 0) && (j != NUM_COLS-1)) ||
                    ((i % 2 == 1) && (j != 0))) begin
                    assign res9_prev[i][j] = st8_9_prev[i][j];
                end

                // Even rows (in the last column) correct bottom right data qubit
                else if (i % 2 == 0) begin
                    leaf_decode dec(.center_in(st8_9_prev[i][j]),
                                    .neighbor_in(1'b1), // artificial syndrome
                                    .correction(st9_corr[i][CODE_DISTANCE-1]),
                                    .center_out(res9_prev[i][j]),
                                    .neighbor_out()); // no neighbor to update
                end

                // Odd rows (in the first column) correct top left data qubit
                else begin
                    leaf_decode dec(.center_in(st8_9_prev[i][j]),
                                    .neighbor_in(1'b1), // artificial syndrome
                                    .correction(st9_corr[i-1][0]),
                                    .center_out(res9_prev[i][j]),
                                    .neighbor_out()); // no neighbor to update
                end
            end
        end

        /*
            FINAL ROUND OF THE BLOCK ONLY: CORRECT EDGE DATA ERRORS IN
            CURRENT SYNDROME
        */
        for (i = 0; i < CODE_DISTANCE; i++) begin
            for (j = 0; j < CODE_DISTANCE; j++) begin
                /* Data qubits untouched in this stage
                    1) Non-first or last columns
                    2) Odd rows in first column
                    3) Odd rows in last column
                */
                if (((j > 0) && (j < CODE_DISTANCE-1)) ||
                    (i % 2 == 1)) begin
                    assign final_corr[i][j] = '0;
                end
            end
        end

        for (i = 0; i < NUM_ROWS; i++) begin
            for (j = 0; j < NUM_COLS; j++) begin
                // Even rows (in the last column) correct bottom right data qubit
                if ((i % 2 == 0) && (j == NUM_COLS-1)) begin
                    leaf_decode dec(.center_in(st8_9_curr[i][j]),
                                    .neighbor_in(1'b1), // artificial syndrome
                                    .correction(final_corr[i][CODE_DISTANCE-1]),
                                    // .center_out(res9_curr[i][j]),
                                    .center_out(), // no need to pass the syndrome any further
                                    .neighbor_out()); // no neighbor to update
                end

                // Odd rows (in the first column) correct top left data qubit
                else if ((i % 2 == 1) && (j == 0)) begin
                    leaf_decode dec(.center_in(st8_9_curr[i][j]),
                                    .neighbor_in(1'b1), // artificial syndrome
                                    .correction(final_corr[i-1][0]),
                                    // .center_out(res9_curr[i][j]),
                                    .center_out(), // no need to pass the syndrome any further
                                    .neighbor_out()); // no neighbor to update
                end
            end
        end
    endgenerate

    // Assign module outputs
    assign valid_out = blk_vld;
    assign complex_out = blk_complex;
    assign corrections_out = blk_corr;
endmodule