"""Option 1: auditable local tools orchestrated by the conversation's agent.

Origin labels record the caller's declaration, not independently verified identity.
No real conversation is generated or inferred by this module.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

VERSION = 'evidence-2026.2'
ORIGINS = {'student_self_report', 'public_document', 'institution_statement',
           'agent_proposal', 'tool_result', 'simulation'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def read_session(path):
    events = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line]
    previous = None
    for i, event in enumerate(events):
        body = {k: v for k, v in event.items() if k != 'hash'}
        if event['sequence'] != i + 1 or event['previous_hash'] != previous or digest(body) != event['hash']:
            raise ValueError('交互记录校验失败')
        previous = event['hash']
    return events


def append_event(path, *, kind, origin, payload, source=None, parent=None, reason=None):
    """Single-writer local ledger; hashes detect edits, not identity or authenticity."""
    if origin not in ORIGINS or kind not in {'input', 'diagnosis', 'proposal', 'evaluation', 'revision', 'risk', 'validation'}:
        raise ValueError('未知事件类型或来源')
    if not isinstance(payload, dict):
        raise ValueError('事件内容须为JSON对象')
    if origin in {'public_document', 'institution_statement'} and not source:
        raise ValueError('公开/高校材料须登记来源与定位')
    if origin == 'student_self_report' and kind != 'input':
        raise ValueError('学生自述只能登记为个体输入，不能直接成为专业诊断或验证结论')
    path = Path(path)
    events = read_session(path) if path.exists() else []
    if kind == 'revision' and (not reason or parent not in {e['hash'] for e in events if e['kind'] in {'proposal', 'revision'}}):
        raise ValueError('修订须引用已有方案并说明修改原因')
    event = dict(sequence=len(events)+1, version=VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(), previous_hash=events[-1]['hash'] if events else None,
        kind=kind, origin=origin, payload=payload, source=source, parent=parent, reason=reason)
    event['hash'] = digest(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False)+'\n')
    return event


def public_summary(path):
    """Allowlist metadata only: never export student payload, sources or path."""
    events = read_session(path)
    return {'version': VERSION, 'event_count': len(events),
        'events': [{'sequence': e['sequence'], 'kind': e['kind'], 'origin': e['origin']} for e in events],
        'notice': '来源标签为调用方声明；链校验不证明身份真实性或高校参与。未导出交互正文。'}


def run_diagnosis(request, session_path=None, data=None):
    from agent.competition import run_competition
    result = run_competition({'program_id': 'BJUT_IM_2024', **request},data)
    result['interaction_method_version'] = VERSION
    result['formal_total_score'] = None
    root = Path(__file__).resolve().parents[1]
    code_paths = ['agent/evidence_session.py','analysis/evidence_metrics.py','analysis/evidence_proposals.py']
    result['interaction_code_hash'] = digest({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in code_paths})
    sources = root/'docs/method_sources.json'
    result['supplemental_method_sources'] = json.loads(sources.read_text(encoding='utf-8')) if sources.exists() else []
    result['formal_teaching_coverage'] = {'point':None,'lower':None,'upper':None,
        'status':'not_identified','reason':'旧词表与课名结果仅探索；任务映射及完整修读路径尚未复核'}
    result['evidence_gate'] = {
        'status': 'requires_task_level_review',
        'message': '旧48标签与课程名称匹配仅作探索；正式覆盖须经任务映射、教学证据及完整修读路径复核。',
        'next_steps': ['依据IS2020建立可观察任务并复核岗位映射', '核对当前教学目标、活动和考核原文',
                       '核验完整选修路径', '补足实际招生及可用资源证据'],
        'student_role': '提供个人情况与质疑，不代表全体学生或高校决策'}
    # The legacy fingerprint covers only the legacy result; identify the wrapped result separately.
    result['interaction_result_hash'] = digest(result)
    if session_path:
        append_event(session_path, kind='diagnosis', origin='tool_result', payload=result)
    return result


def evaluate_and_record(parameters, session_path=None, parent=None, reason=None):
    from analysis.evidence_proposals import evaluate_proposal
    result = evaluate_proposal(**parameters)
    if session_path:
        proposal = append_event(session_path, kind='revision' if parent else 'proposal',
            origin='agent_proposal', payload=parameters, parent=parent, reason=reason)
        append_event(session_path, kind='evaluation', origin='tool_result', payload=result,
            parent=proposal['hash'])
        result['proposal_event_hash'] = proposal['hash']
    return result
