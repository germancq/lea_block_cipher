/**
 * @ Author: German Cano Quiveu, germancq
 * @ Create Time: 2023-10-25 12:30:45
 * @ Modified by: German Cano Quiveu, germancq
 * @ Modified time: 2023-10-26 17:20:27
 * @ Description:
 */

module LEA_enc #(
    parameter KEY_LEN = 128
)
(
    input clk,
    input rst,
    input start_signal,
    input [127:0] plaintext,
    input [191:0] roundkey,
    output logic [4:0] roundkey_addr,
    output logic [127:0] result,
    output logic end_signal
);

    genvar i;

    logic [31:0] X_din [3:0];
    logic [31:0] X_dout [3:0];
    logic [0:0] X_w [3:0];
    logic [0:0] X_cl [3:0];
    generate
        for (i = 0; i<4; i++) begin
            register #(.DATA_WIDTH(32)) r_X_i(
                .clk(clk),
                .cl(X_cl[i]),
                .w(X_w[i]),
                .din(X_din[i]),
                .dout(X_dout[i])
            );
        end
    endgenerate

    assign result = {order_word(X_dout[0]),order_word(X_dout[1]),order_word(X_dout[2]),order_word(X_dout[3])};


    logic [KEY_LEN-1:0] plaintext_reorder;
    generate   
        for (i = 0;i<4;i++) begin
            assign plaintext_reorder[31+(i<<5):(i<<5)] = order_word(plaintext[127-(i<<5):(127-31)-(i<<5)]);
        end
    endgenerate

    logic [31:0] plaintext_reorder_words [3:0];
    generate
        for(i=0;i<4;i++) begin
            assign plaintext_reorder_words[i] = plaintext_reorder[31+(i<<5):(i<<5)];
        end
    endgenerate    

     //round key counter
    logic rk_counter_rst;
    logic rk_counter_down;
    logic [5:0] rk_counter_din;
    logic [5:0] rk_counter_dout;

    generate
        case(KEY_LEN)
            128: begin
                assign rk_counter_din = 24;
            end
            192: begin
                assign rk_counter_din = 28;
            end
            256: begin
                assign rk_counter_din = 32;
            end
            default: begin
                assign rk_counter_din = 24;
            end
        endcase
    endgenerate

    counter #(.DATA_WIDTH(6)) roundkey_counter(
        .clk(clk),
        .rst(rk_counter_rst),
        .up(0),
        .down(rk_counter_down),
        .din(rk_counter_din),
        .dout(rk_counter_dout)
    );

    assign roundkey_addr = rk_counter_din - rk_counter_dout;


    logic [2:0] next_state,current_state;

    localparam IDLE = 0;
    localparam CHECK_ROUNDS = 1;
    localparam CALCULATE_X_1 = 2;
    localparam CALCULATE_X_2 = 3;
    localparam UPDATE_ROUNDS = 4;
    localparam END_STATE = 5;

    logic [31:0] j;
    logic [31:0] k;
    always_comb begin
        next_state = current_state;

        for (j =0 ;j<4 ;j++ ) begin
            X_w[j] = 0;
            X_cl[j] = 0;
            X_din[j] = 32'h0;
        end

        rk_counter_rst = 0;
        rk_counter_down = 0;

        end_signal = 0;

        case (current_state)
            IDLE:begin
                for (j = 0;j<4 ;j++ ) begin
                    X_din[j] = plaintext_reorder_words[j];
                    X_w[j] = 1;
                end

                rk_counter_rst = 1;

                if(start_signal == 1) begin
                    next_state = CHECK_ROUNDS;
                end
            end 
            CHECK_ROUNDS: begin
                next_state = CALCULATE_X_1;
                if(rk_counter_dout == 0) begin
                    next_state = END_STATE;
                end
            end
            CALCULATE_X_1: begin
                for (j = 0;j<3 ;j++ ) begin
                    
                    X_din[j] = (X_dout[j] ^ utils_functions#(192)::getWord(roundkey,5-2*j)) + 
                    (X_dout[j+1] ^ utils_functions#(192)::getWord(roundkey,(5-2*j)-1));
                    
                    X_w[j] = 1;
                end
                X_din[3] = X_dout[0];
                X_w[3] = 1;

                next_state = CALCULATE_X_2;
            end
            CALCULATE_X_2: begin
                X_din[0] = utils_functions#(32)::ROL(X_dout[0],9);
                X_din[1] = utils_functions#(32)::ROR(X_dout[1],5);
                X_din[2] = utils_functions#(32)::ROR(X_dout[2],3);
                for (j = 0;j<3 ;j++ ) begin
                    X_w[j] = 1;
                end

                next_state = UPDATE_ROUNDS;
            end
            UPDATE_ROUNDS: begin
                rk_counter_down = 1;
                next_state = CHECK_ROUNDS;
            end
            END_STATE: begin
                end_signal = 1;
            end

            default: ;
        endcase

    end

    always_ff @(posedge clk) begin
        if (rst) begin
            current_state <= IDLE;
        end
        else begin
            current_state <= next_state;
        end
    end


endmodule: LEA_enc