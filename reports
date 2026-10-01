# Memo: Targeting post-discharge follow-up for diabetic patients

**To:** Director of Care Management | **From:** Lavanya Kaushik, Data Analytics | **Re:** Which discharged patients to call

## Recommendation
Launch the follow-up program with a **risk-ranked call list**, starting at the riskiest **10–20% of diabetic discharges** that current staff can cover. Expand toward **about 50%** as capacity allows, since that size captures 90% of the achievable benefit. Reserve part of the list for **patients aged 80+**, and run the first months as a **measured pilot** to confirm how many readmissions the calls actually prevent.

## Why
- **The model finds the high-risk patients.** The riskiest 10% of discharges are readmitted at 28.6%, 2.5 times the 11.3% average, and account for a quarter of all 30-day readmissions. Scores are calibrated, so a predicted 30% means roughly a 30% chance.
- **Targeting pays for itself.** Assuming a readmission costs $15,000, follow-up costs $200 per patient and prevents 20% of readmissions among those called, a 10% program prevents 5.7 readmissions per 1,000 discharges. That is a net benefit of about **$66,000 per 1,000 discharges**, 4.7 times what the same calls would return if made at random (95% interval $57,000–$75,000).
- **It holds under pessimistic assumptions.** At 10% capacity the program still breaks even if it prevents only 4.7% of readmissions, or if it costs up to $857 per patient.
- **Calling everyone is not the goal.** Net benefit peaks at 78% of discharges and then falls, because the lowest-risk patients cost more to call than they save. Most of the gain comes from the first half of the list.

## What to watch
- **Older patients are under-served.** On a 10% list the model catches only 17.6% of readmissions among patients 80+, against 27.2% for younger patients, because their risk is harder to predict. Reserving some calls for this group, or using a lower risk cut-off for them, closes much of the gap.
- **Insurance type is a top-five driver** and may stand in for income. It should be reviewed before deployment so the list does not disadvantage lower-income patients.
- **The 20% effect is an assumption.** The pilot should compare readmission rates for called and comparable uncalled patients to measure it, then re-set the list size.

## Limits
The model was built on 1999–2008 data from 130 US hospitals, without labs or clinical notes, so it should be validated on current local data first. Savings are from the payer and health-system view; the hospital's own return depends on its payment model and readmission penalties.

*Interactive planner: [Tableau Public dashboard](https://public.tableau.com/views/HospitalReadmissionFollow-upPlanner/Planner). Full analysis: github.com/lavanyakaushik/hospital-readmission-risk.*
