# LabTrace — three-minute demo script

## 0:00–0:25 — Set the context
“LabTrace helps students investigate an engineering experiment while keeping the original readings, calculations, source evidence, and reasoning inspectable. This is a local-first Ohm’s law MVP. The sample values are illustrative demo data, not real lab measurements.”

## 0:25–0:55 — Enter or load readings
Open **Experiment** and click **Load illustrative readings**. Point out the four voltage/current pairs and the lab-manual passage. Save the experiment.

Say: “The interface preserves the original readings instead of replacing them with derived values.”

## 0:55–1:40 — Investigate
Open **Investigation** and click **Run investigation**. Show the original readings beside the calculated results. Highlight Trial 4, then read the caveat: a pattern flag is not proof that a measurement is wrong. Show the possible explanations and evidence/source passage.

If still in mock mode, say explicitly: “This run is labelled DEMO MOCK; it is not Gemma output. The purpose is to validate the student flow before connecting the team harness.”

If integrated, point to the activity trace and identify which calculation/harness stages actually ran. Do not claim a stage ran unless the trace confirms it.

## 1:40–2:20 — Inspect the trace and evidence
Expand or read the activity trace. Explain that the goal is to make tool activity and evidence inspectable, not to show an unexplained AI conclusion. Distinguish calculated results from hypotheses and unverified claims.

## 2:20–2:45 — Viva
Open **Viva**, answer the question about Trial 2 or the inconsistent final reading, and save the answer. Explain that fallback feedback is a basic keyword check; once integrated, the agreed harness should supply evidence-grounded feedback.

## 2:45–3:00 — Persistence and close
Reload the saved experiment from the sidebar or Experiment view.

Close with: “LabTrace connects experiment data, transparent calculations, evidence, and viva practice in one local workflow. The next step is to replace the clearly labelled UI mock with the agreed local Gemma harness and team memory APIs.”
