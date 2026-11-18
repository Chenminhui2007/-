"""Version-isolated inputs for the 2026 competition; no legacy dataset fallback."""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
from pathlib import Path
from functools import cached_property

ROOT=Path(__file__).resolve().parents[1]


class CompetitionData:
    def __init__(self, root: Path | None=None):
        self.root=Path(root) if root is not None else ROOT/'data/competition_2026'
        if not (self.root/'manifest.json').is_file():
            raise FileNotFoundError('校赛数据未导入，请运行 scripts/import_competition_data.py')

    @classmethod
    def load(cls, root: Path | None=None) -> 'CompetitionData':return cls(root)

    def read(self, name: str):
        return json.loads((self.root/(name+'.json')).read_text(encoding='utf-8'))

    @cached_property
    def manifest(self):return self.read('manifest')

    @cached_property
    def programs(self):return self.read('programs')

    @cached_property
    def courses(self):return self.read('courses')

    @cached_property
    def skills(self):return self.read('skills')

    @cached_property
    def jobs(self):
        with gzip.open(self.root/'jobs.csv.gz','rt',encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        for r in rows:
            r['year']=int(r['year']);r['role_groups']=r['role_groups'].split('|') if r['role_groups'] else []
            r['salary_mid']=float(r['salary_mid']) if r['salary_mid'] else None
        return rows

    def program(self, program_id: str):
        for p in self.programs:
            if p['id']==program_id:return dict(p)
        raise ValueError('未知校赛专业版本: '+program_id)

    def program_courses(self, program_id: str):
        self.program(program_id)
        return [dict(c) for c in self.courses if c['program_id']==program_id]

    def provenance(self, ad_ids: set[str]) -> list[dict]:
        month_ids={j['month_id'] for j in self.jobs if j['ad_id'] in ad_ids}
        with gzip.open(self.root/'job_provenance.csv.gz','rt',encoding='utf-8-sig',newline='') as f:
            return [r for r in csv.DictReader(f) if r['month_id'] in month_ids]

    def verify(self, include_raw: bool=False) -> dict:
        errors=[]
        for r in self.manifest['files']:
            p=self.root/r['path']
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:errors.append(r['path'])
        if include_raw:
            for r in self.manifest['raw_sources']:
                p=ROOT/r['path']
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:errors.append(r['path'])
        return {'ok':not errors,'mismatches':errors,'files_checked':len(self.manifest['files']),'raw_checked':include_raw}
