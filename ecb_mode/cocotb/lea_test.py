import os
import random
import sys

import cocotb
import LEA
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

CLK_PERIOD = 20
KEY_LEN = 128
ROUNDS = 24
KEY_128 = 0x0F1E2D3C4B5A69788796A5B4C3D2E1F0
KEY_192 = 0x0F1E2D3C4B5A69788796A5B4C3D2E1F0F0E1D2C3B4A59687
KEY_256 = 0x0F1E2D3C4B5A69788796A5B4C3D2E1F0F0E1D2C3B4A5968778695A4B3C2D1E0F
INPUT_128 = 0x101112131415161718191A1B1C1D1E1F
INPUT_192 = 0x202122232425262728292A2B2C2D2E2F
INPUT_256 = 0x303132333435363738393A3B3C3D3E3F


def setup_block_cipher(dut, key, plaintext):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD, unit="ns").start())
    dut.key.value = key
    dut.rst.value = 0
    dut.block_i.value = plaintext
    dut.rq_data.value = 0


async def rst_function_test(dut):
    dut.rst.value = 1
    await n_cycles_clock(dut, 1)
    assert int(dut.key_sch.current_state.value) == int(
        dut.key_sch.IDLE.value
    ), f"KEY_SCH ERROR STATE IN IDLE, STATE={dut.key_sch.current_state.value}"
    await n_cycles_clock(dut, 10)
    assert int(dut.key_sch.current_state.value) == int(
        dut.key_sch.IDLE.value
    ), f"KEY_SCH ERROR STATE IN IDLE, STATE={dut.key_sch.current_state.value}"
    dut.rst.value = 0


async def round_keys_test(dut):
    # check each T iteration
    lea = LEA.LEA(int(dut.key.value))  # implementacion python
    lea.gen_roundKeys()

    for round in range(0, ROUNDS):
        await n_cycles_clock(dut, 1)

        # check round state
        assert int(dut.key_sch.current_state.value) == int(
            dut.key_sch.CHECK_ROUND.value
        ), f"KEY_SCH ERROR, EXPECTED STATE CHECK_ROUND, STATE={dut.key_sch.current_state.value}"
        # check counter
        assert (
            (ROUNDS) - int(dut.key_sch.rk_counter_dout.value)
        ) == round, f"ERROR in KEY_SCH with the round counter it should be {round}, however it is {(ROUNDS) - dut.key_sch.rk_counter_dout.value}"

        print(round)
        print(hex(dut.key_sch.T_dout[0].value))
        # check T's values
        for i in range(0, int(KEY_LEN / 32)):
            assert (
                lea.T[round][i] == dut.key_sch.T_dout[i].value
            ), f"ERROR in ROUND {round} T{i} should be: {hex(lea.T[round][i])}, however it is {hex(dut.key_sch.T_dout[i].value)}"

        await n_cycles_clock(dut, 1)
        # calculate T step
        assert int(dut.key_sch.current_state.value) == int(
            dut.key_sch.CALCULATE_T_STEP1.value
        ), f"KEY_SCH ERROR, EXPECTED STATE CALCULATE_T_STEP1, STATE={dut.key_sch.current_state.value}"
        print(hex(dut.key_sch.T_dout[0].value))

        await n_cycles_clock(dut, 1)
        # calculate T step 2
        assert int(dut.key_sch.current_state.value) == int(
            dut.key_sch.CALCULATE_T_STEP2.value
        ), f"KEY_SCH ERROR, EXPECTED STATE CALCULATE_T_STEP2, STATE={dut.key_sch.current_state.value}"
        print(hex(dut.key_sch.T_dout[0].value))

        await n_cycles_clock(dut, 1)
        # store rk
        assert int(dut.key_sch.current_state.value) == int(
            dut.key_sch.STORE_RK.value
        ), f"KEY_SCH ERROR, EXPECTED STATE STORE_RK, STATE={dut.key_sch.current_state.value}"

        # check roundkey
        assert (
            lea.roundkeys[round] == dut.key_sch.roundkeys_din.value
        ), f"ERROR GENERATING ROUNDKEYS, RK[{round}] should be {hex(lea.roundkeys[round])}, however it is {hex(dut.key_sch.roundkeys_din.value)}"

        assert (
            round == dut.key_sch.roundkeys_addr.value
        ), f"ERROR GENERATING ROUNDKEYS, RK_addr should be {round}, however it is {int(dut.key_sch.roundkeys_addr.value)}"

        await n_cycles_clock(dut, 1)

        # update_counter
        assert int(dut.key_sch.current_state.value) == int(
            dut.key_sch.UPDATE_COUNTER.value
        ), f"KEY_SCH ERROR, EXPECTED STATE UPDATE_COUNTER, STATE={dut.key_sch.current_state.value}"

    await n_cycles_clock(dut, 2)

    assert int(dut.key_sch.current_state.value) == int(
        dut.key_sch.END_STATE.value
    ), f"KEY_SCH ERROR, EXPECTED STATE END_STATE, STATE={dut.key_sch.current_state.value}"


async def enc_test(dut):

    lea = LEA.LEA(dut.key.value)  # implementacion python
    lea.gen_roundKeys()
    expected_result = lea.encrypt(dut.block_i.value.value)

    assert int(dut.enc_impl.current_state.value) == int(
        dut.enc_impl.IDLE.value
    ), f"ENC ERROR, EXPECTED STATE IDLE, STATE={dut.enc_impl.current_state.value}"

    await n_cycles_clock(dut, 10)

    assert int(dut.enc_impl.current_state.value) == int(
        dut.enc_impl.IDLE.value
    ), f"ENC ERROR, EXPECTED STATE IDLE, STATE={dut.enc_impl.current_state.value}"

    dut.rq_data.value = 1

    for round in range(0, ROUNDS):
        await n_cycles_clock(dut, 1)

        assert int(dut.enc_impl.current_state.value) == int(
            dut.enc_impl.CHECK_ROUNDS.value
        ), f"ENC ERROR, EXPECTED STATE CHECK_ROUNDS, STATE={dut.enc_impl.current_state.value}"

        # check counter
        assert (
            (ROUNDS) - dut.enc_impl.rk_counter_dout.value
        ) == round, f"ERROR in ENC with the round counter it should be {round}, however it is {(ROUNDS) - dut.enc_impl.rk_counter_dout.value}"

        print(round)
        # check X's values
        for i in range(0, 4):
            assert (
                lea.X[round][i] == dut.enc_impl.X_dout[i].value
            ), f"ERROR in ROUND {round} X{i} should be: {hex(lea.X[round][i])}, however it is {hex(dut.enc_impl.X_dout[i].value)}"

        print(hex(dut.enc_impl.X_dout[i].value))
        await n_cycles_clock(dut, 1)

        assert int(dut.enc_impl.current_state.value) == int(
            dut.enc_impl.CALCULATE_X_1.value
        ), f"ENC ERROR, EXPECTED STATE CALCULATE_X_1, STATE={dut.enc_impl.current_state.value}"

        await n_cycles_clock(dut, 1)

        assert int(dut.enc_impl.current_state.value) == int(
            dut.enc_impl.CALCULATE_X_2.value
        ), f"ENC ERROR, EXPECTED STATE CALCULATE_X_2, STATE={dut.enc_impl.current_state.value}"

        await n_cycles_clock(dut, 1)

        assert int(dut.enc_impl.current_state.value) == int(
            dut.enc_impl.UPDATE_ROUNDS.value
        ), f"ENC ERROR, EXPECTED STATE UPDATE_ROUNDS, STATE={dut.enc_impl.current_state.value}"

    await n_cycles_clock(dut, 2)

    assert int(dut.enc_impl.current_state.value) == int(
        dut.enc_impl.END_STATE.value
    ), f"ENC ERROR, EXPECTED STATE END_STATE, STATE={dut.enc_impl.current_state.value}"

    assert (
        expected_result == dut.enc_impl.result.value
    ), f"ENC ERROR, WRONG RESULT, expected = {hex(expected_result)}, however it is {hex(dut.enc_impl.result.value)}"


async def n_cycles_clock(dut, n):
    for i in range(0, n):
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)


@cocotb.test()
@cocotb.parametrize(index=range(0, 10))
async def testLUA(dut, index=0):
    global KEY_LEN
    global ROUNDS

    KEY_LEN = dut.KEY_LEN.value
    ROUNDS = 24
    BLOCK_LEN = 128
    if KEY_LEN == 192:
        ROUNDS = 28
    elif KEY_LEN == 256:
        ROUNDS = 32

    key = random.getrandbits(KEY_LEN)
    block = random.getrandbits(BLOCK_LEN)
    print(f"key is = {hex(key)}")

    setup_block_cipher(dut, key, block)
    await rst_function_test(dut)
    await round_keys_test(dut)
    await enc_test(dut)
