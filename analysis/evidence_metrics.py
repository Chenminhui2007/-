"""Task-level evidence metrics v2. Unknown evidence is not a zero score."""
from math import isfinite
import hashlib
import json

VERSION = 'evidence-2026.2'


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def coverage(tasks, postings, evidence, *, curriculum_version, path_verified=False, evidence_snapshot=None):
    ids = [t['id'] for t in tasks]
    if len(ids) != len(set(ids)) or not ids or any(not isinstance(k,str) or not k.strip() for k in ids):
        raise ValueError('任务编号必须非空且唯一')
    if any(not t.get('definition') or not t.get('framework_reference') for t in tasks):
        raise ValueError('任务须有可观察定义及框架原文定位')
    known = set(ids)
    seen = set()
    counts = dict.fromkeys(ids, 0)
    for row in postings:
        if row['id'] in seen:
            raise ValueError('广告ID重复，须先按固定口径去重')
        seen.add(row['id'])
        labels = set(row['task_ids'])
        if labels-known:
            raise ValueError('广告含未定义任务')
        for task in labels:
            counts[task] += 1
    states = {k: set() for k in ids}
    rejected = []
    for row in evidence:
        task = row.get('task_id')
        valid = (task in known and row.get('curriculum_version') == curriculum_version
                 and row.get('source_id') and row.get('locator') and row.get('reviewer')
                 and row.get('scope') == 'current_teaching')
        status = row.get('status')
        if status == 'C':
            valid = valid and all(row.get(k) for k in ('outcome', 'activity', 'assessment')) and row.get('task_level_review') is True
        elif status == 'A':
            valid = valid and row.get('full_path_reviewed') is True and row.get('absence_reason')
        else:
            valid = False
        if valid:
            states[task].add(status)
        else:
            rejected.append(row.get('id', task))
    resolved = {k: next(iter(v)) if len(v) == 1 else 'U' for k, v in states.items()}
    mass = sum(counts.values())
    weights = {k: counts[k]/mass if mass else None for k in ids}
    lower = sum(weights[k] for k in ids if resolved[k] == 'C')*100 if mass else None
    upper = sum(weights[k] for k in ids if resolved[k] != 'A')*100 if mass else None
    unknown = sum(weights[k] for k in ids if resolved[k] == 'U')*100 if mass else None
    ready = path_verified is True and all(t.get('mapping_reviewed') is True for t in tasks)
    measurement = {'tasks':sorted(tasks,key=lambda t:t['id']),
        'postings':sorted([{'id':r['id'],'task_ids':sorted(set(r['task_ids']))} for r in postings],key=lambda r:r['id']),
        'evidence_snapshot':evidence_snapshot, 'scope':'current_teaching', 'version':VERSION}
    measurement_hash = hashlib.sha256(json.dumps(measurement,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return dict(method_version=VERSION, rows=[dict(task_id=k, count=counts[k],
        prevalence=counts[k]/len(postings) if postings else None, weight=weights[k], state=resolved[k]) for k in ids],
        lower=lower if ready else None, upper=upper if ready else None,
        unknown_weight=unknown if ready else None,
        point=lower if ready and unknown == 0 else None,
        score_status='identified' if ready and unknown == 0 and mass else 'not_identified',
        blockers=([] if path_verified is True else ['修读路径未完成核验'])+
                 ([] if all(t.get('mapping_reviewed') is True for t in tasks) else ['能力映射未复核']),
        rejected_evidence=rejected, conflicts=[k for k,v in states.items() if len(v)>1],
        measurement_hash=measurement_hash,evidence_snapshot=evidence_snapshot,
        total_score=None, label='需求加权教学证据覆盖；非学生达成率')


def resource_pressure(rows):
    result=[]
    for r in rows:
        demand,available=r.get('demand'),r.get('available')
        if not finite(demand) or demand < 0 or (available is not None and (not finite(available) or available < 0)):
            raise ValueError('资源数量必须非负有限，未知用null')
        if not r.get('unit') or not r.get('period'):
            raise ValueError('资源须有单位与期间')
        verified=r.get('availability_verified') is True and bool(r.get('source_id'))
        result.append(dict(id=r['id'],unit=r['unit'],period=r['period'],demand=demand,available=available,
            ratio=demand/available if available else None,
            shortfall=max(0,demand-available) if available is not None else None,
            status='unknown' if available is None else ('verified' if verified else 'conditional'),
            overload=demand>available if available is not None else None))
    return result


def compare_coverage(before,after,*,same_measurement=False):
    if same_measurement is not True:
        return {'delta':None,'reason':'未确认相同样本、任务、权重、路径范围与证据层次'}
    if (not before.get('evidence_snapshot') or before.get('measurement_hash') != after.get('measurement_hash')
            or not before.get('measurement_hash')):
        return {'delta':None,'reason':'缺少共同证据快照，或任务/样本/权重口径不一致'}
    values=[before.get('lower'),before.get('upper'),after.get('lower'),after.get('upper')]
    if any(v is None for v in values):
        return {'delta':None,'reason':'覆盖尚不可识别'}
    if any(not finite(v) for v in values) or not (0<=values[0]<=values[1]<=100 and 0<=values[2]<=values[3]<=100):
        raise ValueError('覆盖区间须为0—100内的有限有序数值')
    return {'delta':{'lower':values[2]-values[1],'upper':values[3]-values[0]},
            'interpretation':'保守识别范围，不是置信区间或因果效果'}
