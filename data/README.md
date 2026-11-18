# Local data only

Public example files live in examples/evidence_v2 and are synthetic.
For private competition diagnosis put the authorized frozen data under data/competition_2026 or pass --data-root.
Required files: manifest.json, programs.json, courses.json, skills.json, jobs.csv.gz,
job_provenance.csv.gz, curriculum_totals.json, geography_flags.json, cluster_flags.json,
reviewed_teaching_evidence.json, admissions.json, resources.json, outcomes.json, literature.json.
manifest.files holds relative path and sha256; manifest.raw_sources and limitations retain provenance and limits.
The loader rejects changed hashes. Do not commit the actual dataset or replace unknown teaching/capacity with fabricated values.
The upstream data loader and scripts are retained as source; original contest archives and external intermediate directories are not distributed.
