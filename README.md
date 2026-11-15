# Digital Clock Using Logic Gates

24-hour HH:MM:SS digital clock designed with logic gates and JK flip-flops
(Subject: Digital Electronics and Circuits).

## Files
| File | Description |
|---|---|
| `digital_clock_sim.py` | Gate-level simulation of the clock (JK flip-flops, AND, OR, NOT gates) and test of the BCD to seven-segment decoder |
| `Digital_Clock_Logic_Gates_Report_Corrected.docx` | Project report |
| `Digital_Clock_Project_Presentation.pptx` | Project presentation |

## How to run
Python 3 is required. No extra libraries are needed.

```
python3 digital_clock_sim.py
```

## What the program does
1. **Decoder test** - checks the seven decoder equations (Table 4 of the report) for digits 0 to 9.
2. **Continuous run** - runs 172,800 one-second pulses (48 hours) and compares every display with the correct time.
3. **Rollover test** - 00:00:09, 00:59:59, 09:59:59 and 23:59:59 (Table 6 of the report).
4. **Set-time and reset test** - minute and hour push buttons, and reset to 00:00:00.

Expected output: `10 of 10 correct`, `Mismatches: 0` and `ALL TESTS PASSED`.

## Design summary
- Time base: 32.768 kHz crystal divided by 2^15 gives 1 Hz.
- Seconds and minutes: MOD-10 (units) and MOD-6 (tens) synchronous counters.
- Hours: MOD-24 counter that returns to 00 after 23.
- Carry chain: AND gates; display: BCD to seven-segment decoders.

## Repository
https://github.com/YOUR-USERNAME/digital-clock-project
