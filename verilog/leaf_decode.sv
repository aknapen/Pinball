module leaf_decode #(
    NUM_CORR_BITS=1
)
(
    input center_in,
    input neighbor_in,

    output[NUM_CORR_BITS-1:0] correction,
    output center_out,
    output neighbor_out
);
    genvar i;
    generate
        for (i = 0; i < NUM_CORR_BITS; i++) begin
            assign correction[i] = center_in * neighbor_in;
        end
    endgenerate
    
    // Clear the ancillas if a correction will be applied
    assign center_out = center_in ^ correction;
    assign neighbor_out = neighbor_in ^ correction;
endmodule