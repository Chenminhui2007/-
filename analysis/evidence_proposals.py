"""Non-compensatory proposal checks. A valid structure is not educational approval."""
from analysis.competition_actions import evaluate_actions, risk_register
from analysis.evidence_metrics import resource_pressure, VERSION


def evaluate_proposal(courses, actions, *, literature_ids, task_ids, resources=None,
                      budget=None, totals=(), selected_electives=(), selected_electives_after=None):
    evaluation = evaluate_actions(courses, actions, literature_ids=literature_ids,
        skill_ids=task_ids, budget=budget, totals=totals, selected_electives=selected_electives,
        selected_electives_after=selected_electives_after)
    errors = list(evaluation['errors'])
    gaps = []
    for action in actions:
        support = action.get('evidence_support', [])
        supported = {s.get('source_id') for s in support if isinstance(s,dict)
                     and s.get('locator') and s.get('claim') and s.get('support_reviewed') is True}
        if not set(action.get('literature_ids', [])) <= supported:
            gaps.append(f"{action.get('id')}: 文献尚缺原文定位、支持论断或语义复核")
        if action.get('task_mapping_reviewed') is not True:
            gaps.append(f"{action.get('id')}: 能力任务映射未复核")
    pressure = resource_pressure(resources or [])
    if not pressure:
        gaps.append('尚未逐资源登记需求与同期可用容量')
    for row in pressure:
        if row['status'] != 'verified':
            gaps.append(f"{row['id']}: 容量为未知或条件假设")
        if row['overload']:
            errors.append(f"{row['id']}: 当前资源输入下超载；缺口{row['shortfall']} {row['unit']}")
    status = 'infeasible_under_inputs' if errors else ('conditional' if gaps else 'checks_passed_pending_educational_review')
    return {'method_version': VERSION, 'status':status, 'errors':errors, 'evidence_gaps':gaps,
        'curriculum_constraints':evaluation, 'resource_pressure':pressure,
        'candidate_actions':actions, 'accepted_for_comparison':bool(actions) and not errors,
        'implemented':False, 'institution_approved':False, 'total_score':None,
        'risks':risk_register([a['id'] for a in actions if a.get('id')]),
        'interpretation':'通过代码检查不等于教育合理、学校批准或真实学习有效；条件方案不得表述为资源已证实可行。'}
