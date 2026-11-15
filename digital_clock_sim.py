#!/usr/bin/env python3
"""
Digital Clock Using Logic Gates - gate-level simulation
=======================================================
Project report: "Digital Clock Using Logic Gates"
Subject       : Digital Electronics and Circuits

This program models the 24-hour HH:MM:SS clock exactly as designed in the
report. Every flip-flop follows the JK characteristic equation

        Q+ = J.Q' + K'.Q

and every J/K input is built only from AND, OR and NOT operations, using the
equations of Chapter 3 of the report:

    * MOD-10 counter (units of seconds / minutes)    - Section 3.3
    * MOD-6  counter (tens  of seconds / minutes)    - Section 3.4
    * AND-gate carry chain                           - Section 3.5
    * MOD-24 hours counter                           - Section 3.6
    * BCD to seven-segment decoder (Table 4)         - Section 3.7
    * Time-set logic (push buttons)                  - Section 3.8
    * Power-on reset to 00:00:00                     - Section 3.9

The model is synchronous: in every clock pulse all J and K inputs are first
computed from the PRESENT state, and then all flip-flops change together.

Run:   python3 digital_clock_sim.py
"""

# --------------------------------------------------------------------------
# 1. Basic gates (single-bit, values 0 or 1)
# --------------------------------------------------------------------------
def NOT(a):
    return 1 - a


def AND(*inputs):
    result = 1
    for v in inputs:
        result &= v
    return result


def OR(*inputs):
    result = 0
    for v in inputs:
        result |= v
    return result


# --------------------------------------------------------------------------
# 2. JK flip-flop:  Q+ = J.Q' + K'.Q
# --------------------------------------------------------------------------
def jk_ff(q, j, k):
    """Next state of a JK flip-flop (hold, reset, set, toggle)."""
    return OR(AND(j, NOT(q)), AND(NOT(k), q))


# --------------------------------------------------------------------------
# 3. Synchronous counters.  State tuples are written (Q1, Q2, Q4, Q8).
#    E is the enable input: E = 1 counts, E = 0 freezes the counter.
# --------------------------------------------------------------------------
def mod10_next(state, E):
    """MOD-10 counter 0..9 (Section 3.3)."""
    q1, q2, q4, q8 = state
    j1 = k1 = E
    j2 = AND(NOT(q8), q1, E)
    k2 = AND(q1, E)
    j4 = k4 = AND(q2, q1, E)
    j8 = AND(q4, q2, q1, E)
    k8 = AND(q1, E)
    return (jk_ff(q1, j1, k1), jk_ff(q2, j2, k2),
            jk_ff(q4, j4, k4), jk_ff(q8, j8, k8))


def mod6_next(state, E):
    """MOD-6 counter 0..5 (Section 3.4).  State is (Q1, Q2, Q4)."""
    q1, q2, q4 = state
    j1 = k1 = E
    j2 = AND(NOT(q4), q1, E)
    k2 = AND(q1, E)
    j4 = AND(q2, q1, E)
    k4 = AND(q1, E)
    return (jk_ff(q1, j1, k1), jk_ff(q2, j2, k2), jk_ff(q4, j4, k4))


def hours_next(units, tens, E_hu):
    """MOD-24 hours counter 00..23 (Section 3.6).

    units = (U1, U2, U4, U8)      tens = (T1, T2)
    C = U8.U1.E_hu   ("units = 9" carry)
    Z = T2.U2.U1     (hour 23 detector)
    """
    u1, u2, u4, u8 = units
    t1, t2 = tens
    C = AND(u8, u1, E_hu)
    Z = AND(t2, u2, u1)

    # units: as MOD-10, except J4 is blocked at 23 by Z'
    j1 = k1 = E_hu
    j2 = AND(NOT(u8), u1, E_hu)
    k2 = AND(u1, E_hu)
    j4 = AND(u2, u1, E_hu, NOT(Z))
    k4 = AND(u2, u1, E_hu)
    j8 = AND(u4, u2, u1, E_hu)
    k8 = AND(u1, E_hu)
    new_units = (jk_ff(u1, j1, k1), jk_ff(u2, j2, k2),
                 jk_ff(u4, j4, k4), jk_ff(u8, j8, k8))

    # tens
    jt1 = AND(NOT(t2), C)
    kt1 = C
    jt2 = AND(t1, C)
    kt2 = AND(Z, E_hu)
    new_tens = (jk_ff(t1, jt1, kt1), jk_ff(t2, jt2, kt2))
    return new_units, new_tens


# --------------------------------------------------------------------------
# 4. BCD to seven-segment decoder (Table 4 of the report)
#    Inputs A (MSB), B, C, D (LSB).  Common-cathode: segment lit when 1.
# --------------------------------------------------------------------------
def decoder_7seg(digit):
    A, B, C, D = (digit >> 3) & 1, (digit >> 2) & 1, (digit >> 1) & 1, digit & 1
    nB, nC, nD = NOT(B), NOT(C), NOT(D)
    a = OR(A, C, AND(B, D), AND(nB, nD))
    b = OR(nB, AND(nC, nD), AND(C, D))
    c = OR(B, nC, D)
    d = OR(A, AND(nB, nD), AND(nB, C), AND(C, nD), AND(B, nC, D))
    e = OR(AND(nB, nD), AND(C, nD))
    f = OR(A, AND(nC, nD), AND(B, nC), AND(B, nD))
    g = OR(A, AND(B, nC), AND(nB, C), AND(C, nD))
    return "".join(str(v) for v in (a, b, c, d, e, f, g))


# Standard seven-segment patterns (a b c d e f g), used only to CHECK the
# decoder; they are written down independently of the equations above.
STANDARD_PATTERNS = {
    0: "1111110", 1: "0110000", 2: "1101101", 3: "1111001", 4: "0110011",
    5: "1011011", 6: "1011111", 7: "1110000", 8: "1111111", 9: "1111011",
}


# --------------------------------------------------------------------------
# 5. The complete clock
# --------------------------------------------------------------------------
def bits_to_int(bits):
    """(Q1, Q2, Q4, Q8, ...) -> decimal value."""
    return sum(bit << i for i, bit in enumerate(bits))


class DigitalClock:
    def __init__(self):
        self.reset()

    def reset(self):
        """Power-on / manual reset: every flip-flop is cleared (00:00:00)."""
        self.su = (0, 0, 0, 0)   # seconds units
        self.st = (0, 0, 0)      # seconds tens
        self.mu = (0, 0, 0, 0)   # minutes units
        self.mt = (0, 0, 0)      # minutes tens
        self.hu = (0, 0, 0, 0)   # hours units
        self.ht = (0, 0)         # hours tens

    def pulse(self, set_minutes=0, set_hours=0):
        """Apply one 1 Hz clock pulse.  set_minutes / set_hours model the
        debounced push buttons (Section 3.8)."""
        su1, su2, su4, su8 = self.su
        st1, st2, st4 = self.st
        mu1, mu2, mu4, mu8 = self.mu
        mt1, mt2, mt4 = self.mt

        # Carry chain (Section 3.5), computed from the present state
        E_su = 1
        E_st = AND(su8, su1)                       # seconds units = 9
        E_mu = AND(E_st, st4, st1)                 # seconds = 59
        E_mu = OR(E_mu, set_minutes)               # set-minutes button
        E_mt = AND(E_mu, mu8, mu1)                 # minutes units = 9
        E_hc = AND(E_mt, mt4, mt1)                 # minutes = 59
        E_hu = OR(AND(E_hc, NOT(set_minutes)), set_hours)

        # All flip-flops change together (synchronous operation)
        new_su = mod10_next(self.su, E_su)
        new_st = mod6_next(self.st, E_st)
        new_mu = mod10_next(self.mu, E_mu)
        new_mt = mod6_next(self.mt, E_mt)
        new_hu, new_ht = hours_next(self.hu, self.ht, E_hu)

        self.su, self.st, self.mu, self.mt = new_su, new_st, new_mu, new_mt
        self.hu, self.ht = new_hu, new_ht

    def digits(self):
        """The six displayed digits (HT, HU, MT, MU, ST, SU)."""
        return (bits_to_int(self.ht), bits_to_int(self.hu),
                bits_to_int(self.mt), bits_to_int(self.mu),
                bits_to_int(self.st), bits_to_int(self.su))

    def time_string(self):
        d = self.digits()
        return f"{d[0]}{d[1]}:{d[2]}{d[3]}:{d[4]}{d[5]}"

    def segments(self):
        """Segment patterns sent to the six displays."""
        return [decoder_7seg(d) for d in self.digits()]


def expected_time(pulses):
    """Correct time worked out independently by ordinary arithmetic."""
    total = pulses % 86400
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# --------------------------------------------------------------------------
# 6. Tests
# --------------------------------------------------------------------------
def test_decoder():
    print("TEST 1 - BCD to seven-segment decoder (digits 0 to 9)")
    print("  digit  a b c d e f g   result")
    ok = 0
    for digit in range(10):
        got = decoder_7seg(digit)
        good = got == STANDARD_PATTERNS[digit]
        ok += good
        print(f"    {digit}    {' '.join(got)}   {'OK' if good else 'WRONG'}")
    print(f"  Result: {ok} of 10 correct\n")
    return ok == 10


def test_continuous(pulses=172800):
    print(f"TEST 2 - Continuous run of {pulses:,} pulses "
          f"({pulses // 3600} hours)")
    clock = DigitalClock()
    mismatches = 0
    invalid_hour = 0
    midnights = 0
    previous = clock.time_string()
    for n in range(1, pulses + 1):
        clock.pulse()
        shown = clock.time_string()
        if shown != expected_time(n):
            mismatches += 1
        if int(shown[:2]) > 23:
            invalid_hour += 1
        if shown == "00:00:00":
            midnights += 1
            assert previous == "23:59:59"
        previous = shown
    print(f"  Mismatches        : {mismatches}")
    print(f"  Invalid hours (24): {invalid_hour}")
    print(f"  Midnight rollovers: {midnights} (23:59:59 -> 00:00:00)")
    print(f"  Final display     : {clock.time_string()}\n")
    return mismatches == 0 and invalid_hour == 0


def test_rollovers():
    print("TEST 3 - Rollover examples (Table 6 of the report)")
    cases = [(9, "00:00:09", "00:00:10"),
             (3599, "00:59:59", "01:00:00"),
             (36000 - 1, "09:59:59", "10:00:00"),
             (86400 - 1, "23:59:59", "00:00:00")]
    all_ok = True
    clock = DigitalClock()
    n = 0
    for target, before, after in cases:
        while n < target:
            clock.pulse()
            n += 1
        b = clock.time_string()
        clock.pulse()
        n += 1
        a = clock.time_string()
        good = (b == before and a == after)
        all_ok &= good
        print(f"  {b} -> {a}   {'OK' if good else 'WRONG'}")
    print()
    return all_ok


def test_set_time_and_reset():
    print("TEST 4 - Time setting (Section 3.8) and reset (Section 3.9)")
    clock = DigitalClock()
    for _ in range(60):
        clock.pulse(set_minutes=1)
    c1 = clock.time_string()[:5] == "00:00"      # minutes wrapped, hours unchanged
    print(f"  60 minute-set pulses : {clock.time_string()}  "
          f"(hours must stay 00) {'OK' if c1 else 'WRONG'}")
    clock.reset()
    for _ in range(30):
        clock.pulse(set_hours=1)
    c2 = clock.time_string()[:2] == "06"          # 30 mod 24 = 6, never 24
    print(f"  30 hour-set pulses   : {clock.time_string()}  "
          f"(30 mod 24 = 06) {'OK' if c2 else 'WRONG'}")
    clock.reset()
    c3 = clock.time_string() == "00:00:00"
    print(f"  After reset          : {clock.time_string()}  "
          f"{'OK' if c3 else 'WRONG'}\n")
    return c1 and c2 and c3


def main():
    print("=" * 60)
    print(" DIGITAL CLOCK USING LOGIC GATES - GATE-LEVEL SIMULATION")
    print("=" * 60 + "\n")
    results = [test_decoder(), test_continuous(), test_rollovers(),
               test_set_time_and_reset()]
    print("=" * 60)
    print(" ALL TESTS PASSED" if all(results) else " SOME TESTS FAILED")
    print("=" * 60)
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
