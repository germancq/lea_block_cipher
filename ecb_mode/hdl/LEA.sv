/**
 * @ Author: German Cano Quiveu, germancq
 * @ Create Time: 2023-05-04 16:06:30
 * @ Modified by: German Cano Quiveu, germancq
 * @ Modified time: 2023-11-20 17:48:05
 * @ Description:
 */


import common_functions::*;

`define DEBUG_LEA


module LEA #(
    parameter KEY_LEN = 128
) (
    input clk,
    input rst,
    input [KEY_LEN-1:0] key,
    input [127:0] block_i,
    output [127:0] block_o,
    input rq_data,
    output end_key_generation,
    output end_signal

);




  logic r_w_roundkeys;
  logic [4:0] addr_roundkeys;
  logic [191:0] din_roundkeys;
  logic [191:0] dout_roundkeys;

  logic [4:0] addr_roundkeys_ks;
  logic [4:0] addr_roundkeys_crypto;

  logic r_w_roundkeys_ks;
  logic r_w_roundkeys_crypto;

  assign r_w_roundkeys_crypto = 0;

  logic start_enc;
  logic [127:0] result_enc;
  logic end_enc;

  assign end_signal = end_enc;

  mux #(
      .DATA_WIDTH(5)
  ) mux_roundkeys_addr (
      .a  (addr_roundkeys_ks),
      .b  (addr_roundkeys_crypto),
      .sel(end_key_generation),
      .c  (addr_roundkeys)
  );

  mux #(
      .DATA_WIDTH(1)
  ) mux_roundkeys_rw (
      .a  (r_w_roundkeys_ks),
      .b  (r_w_roundkeys_crypto),
      .sel(end_key_generation),
      .c  (r_w_roundkeys)
  );

  register #(
      .DATA_WIDTH(128)
  ) result (
      .clk(clk),
      .cl(rst || rq_data),
      .w(end_enc),
      .din(result_enc),
      .dout(block_o)
  );

  memory_module #(
      .ADDR(5),
      .DATA_WIDTH(192)
  ) roundkeys_mem (
      .clk (clk),
      .r_w (r_w_roundkeys),
      .addr(addr_roundkeys),
      .din (din_roundkeys),
      .dout(dout_roundkeys)
  );

  key_schedule #(
      .KEY_LEN(KEY_LEN)
  ) key_sch (
      .clk(clk),
      .rst(rst),
      .key(key),
      .roundkeys_addr(addr_roundkeys_ks),
      .roundkeys_din(din_roundkeys),
      .roundkeys_rw(r_w_roundkeys_ks),
      .end_key_generation(end_key_generation)
  );

  LEA_enc #(
      .KEY_LEN(KEY_LEN)
  ) enc_impl (
      .clk(clk),
      .rst(rst),
      .start_signal(rq_data && end_key_generation),
      .plaintext(block_i),
      .roundkey(dout_roundkeys),
      .roundkey_addr(addr_roundkeys_crypto),
      .result(result_enc),
      .end_signal(end_enc)
  );

endmodule : LEA





