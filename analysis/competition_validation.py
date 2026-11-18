"""Semantic quality gate for competition-2026.1 results."""
import math


def validate_result(result):
    checks=[]
    def check(name,ok,message): checks.append({'check':name,'level':'ok' if ok else 'error','message':message})
    def finite(x):
        if isinstance(x,float): return math.isfinite(x)
        if isinstance(x,dict): return all(finite(v) for v in x.values())
        if isinstance(x,list): return all(finite(v) for v in x)
        return True
    check('finite',finite(result),'数值无NaN/Infinity')
    d=result['diagnosis']; strict=d['skills']['strict_coverage']; demand=d['skills']['demand']
    check('three_dimensions',all(k in d for k in ('skills','directions','scale')),'三维分列')
    check('coverage_bounds',strict['lower'] is None or -1e-9<=strict['lower']<=strict['upper']<=1+1e-9,'覆盖识别边界在[0,1]')
    check('unknown_point',strict['unknown_weight'] in (None,0) or strict['point'] is None,'未知教学覆盖不输出确定分数')
    check('prevalence',all(s['prevalence'] is None or 0<=s['prevalence']<=1+1e-9 for s in demand['skills']),'广告技能出现率有合法分母')
    check('relative_weights',not any(s['relative_weight'] for s in demand['skills']) or abs(sum(s['relative_weight'] or 0 for s in demand['skills'])-1)<1e-8,'摘要权重和为1或无可用提及')
    check('actual_missing',d['scale']['actual_admissions'] is None and d['scale']['verified_additional_capacity'] is None,'未核实实际录取和余量保持缺失')
    check('auxiliary_no_invention',d['auxiliary_tsi']['value'] is None,'无完整同口径输入时不编综合分')
    sim=result['simulation']; runs=sim['runs']
    check('scenarios',not runs or len(runs)>=3,'至少三个情景（对照无基准时不可计算）')
    check('horizon',all(len(r['rows'])>=4 for r in runs),'推演不少于四年')
    rows=[r for run in runs for r in run['rows']]
    check('conditional_labels',all(r['recommended_intake'] is None and r['observed_employment_rate'] is None for r in rows),'条件路径未变成真实招生建议或就业结果')
    check('unknown_stock',all(r[a]['total_in_school'] is None for r in rows for a in ('baseline','adjusted')),'初始年级未知时不补总在校生')
    check('paired_baseline',all(r['baseline']['conditional_intake']==run['baseline_plan'] for run in runs for r in run['rows']),'不调整基线固定于真实2025计划')
    check('cohort_delay',all(r['adjusted']['modelled_graduates'] is None for run in runs for r in run['rows'] if r['year']<run['first_modelled_graduation_year']),'毕业输出遵守培养时滞')
    check('feedback_delay',all(r['employment_feedback_assumption'] is None for run in runs for r in run['rows'] if r['year']<run['first_feedback_year']),'反馈不早于模型队列毕业次年')
    check('risks',len(result['risks'])>=3 and all(r['action_ids'] and r['trigger'] and r['response'] for r in result['risks']),'至少三项行动关联风险')
    check('risk_probability',all(r['probability'] is None for r in result['risks']),'未校准风险概率保持未知')
    check('trace',bool(result['tool_trace']) and bool(result['input_fingerprint']),'工具轨迹与输入指纹存在')
    check('rejected_not_accepted',result['curriculum_proposal']['valid'] or not result['accepted_actions'],'失败动作不进入情景')
    check('allocation',result['allocation'] is None or result['allocation']['stable'],'分流结果没有阻塞对')
    return {'ok':all(c['level']=='ok' for c in checks),'checks':checks,'count':len(checks)}
