# Ohm's Law — Reference for Lab Investigator

## The Law

Ohm's law states that the voltage (V) across an ohmic conductor is
directly proportional to the current (I) flowing through it, provided
physical conditions (such as temperature) remain constant:

    V = I × R

where **R** is the resistance of the conductor, measured in ohms (Ω).

## Calculating Resistance

Rearranging the formula gives:

    R = V / I

This is valid only when the current **I is not zero**. If the current
reading is zero, resistance cannot be calculated — it does not mean
the resistance is infinite; it usually means the circuit is open or
the reading is faulty.

## Expected Behaviour of an Ohmic Conductor

For a component that obeys Ohm's law (e.g. a standard metal-film
resistor at room temperature):

- Plotting voltage against current should produce a **straight line
  through the origin**.
- The **gradient** (slope) of that line equals the resistance R.
- Every reading pair (V, I) should give approximately the **same
  value of R**, within normal measurement uncertainty.

## Interpreting Inconsistent Readings

If one or more readings give a noticeably different resistance:

1. **Do not immediately discard the reading.** It is real data.
2. **Compare it** to the other readings quantitatively (e.g. "this
   reading gives R = 200 Ω while the others give R ≈ 100 Ω").
3. **Consider possible causes**, but label them as hypotheses:
   - A loose or corroded connection may have introduced extra
     resistance.
   - The component may have heated up, changing its resistance
     (real resistors have a temperature coefficient).
   - The reading may have been recorded incorrectly (e.g. the
     current was misread from the ammeter scale).
   - A different resistor may have been connected by mistake.
4. **Suggest verification steps**: repeat the measurement, check
   connections, measure the resistor independently with an ohmmeter,
   or inspect the ammeter/voltmeter for parallax or range errors.

## Limitations

- Ohm's law applies only to **ohmic conductors**. Components like
  diodes, thermistors, and filament lamps do not obey it.
- Real measurements always contain some uncertainty. Small
  deviations between readings are normal; only large, systematic
  deviations warrant investigation.
- Temperature changes during the experiment can alter resistance.
  This is especially relevant for long-duration tests or high
  currents.
- Instrument precision limits the number of significant figures
  that can be trusted in a calculated result.

## Key Terms

| Term | Meaning |
|---|---|
| Voltage (V) | Electrical potential difference, measured in volts (V) |
| Current (I) | Flow of electric charge, measured in amperes (A) |
| Resistance (R) | Opposition to current flow, measured in ohms (Ω) |
| Ohmic conductor | A material where V/I is constant (at constant temperature) |
| Anomaly | A reading that does not fit the pattern of the other readings |
