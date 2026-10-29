# Build outputs

`make build` writes every mart, analysis table, the FP&A model tables and
`delta_fpna_foundation.sqlite` here. These files are regenerated on every build and are not
committed. The compact tables the dashboard and Tableau use are copied to `data/published/`
and `tableau/`, which are committed.
