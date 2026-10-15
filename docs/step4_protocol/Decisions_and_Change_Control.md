# Protocol v1.0 decisions and amendments from draft

2026-10-15; before any model fitting or controller outcomes.

1. Freeze budgets250/150 ms now; do not claim development feasibility has been established. This changes the earlier proposal to check feasibility before committing to budgets.
2. Define common-denominator offset compliance and report actual release delays separately for active pre-offset cases. Already-inactive cases are flagged rather than credited as fast physical releases.
3. Add an80% nonzero active-interior coverage guard to prevent degenerate suppression. It is a design goal, not a clinical standard; wrong-class output remains a separate error metric.
4. Explicitly allocate natural rest by half-open midpoint cells; merge only touching cells of the same role. Use a common250 ms warmup exclusion and time-weighted output occupancy.
5. Use dev people1–2 reps2/5/6 for global policy selection; fit each personalized decoder on1/3/4. For final people3–10, evaluate2/5 and leave6 unused.
6. Remove independently tuned direct-switch persistence because the primary data contain no direct annotated switches. Use activation count for active-to-active changes in the asymmetric policy; do not claim direct-switch validity.
7. Freeze the original three-feature starter set, standardized shrinkage LDA, complete107-candidate comparison and descriptive infeasibility fallback. Selected configurations remain a Step7 output.
8. Define the OTVL-inspired envelope/peak-confirmation adaptation as exploratory, not a faithful reproduction. Velocity and glove extensions remain outside confirmatory v1.0.
9. Prespecify participant-level analysis, secondary multiplicity correction, sensitivities and conditional DB2 replication. DB2 compatibility remains to be checked before its fitting.

No final-data-driven amendment occurred. There is no public preregistration record. Any future change must be appended as a new numbered version with exposure history; do not overwrite frozen v1.0 files.
