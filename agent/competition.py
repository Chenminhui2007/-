"""Offline competition workflow exposed identically through CLI, UI and MCP."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
from typing import Any

from edumatch.competition_data import CompetitionData, ROOT
from analysis.competition_metrics import diagnose, compare_proposed_path
from analysis.competition_actions import evaluate_actions, allocate_directions, risk_register
from analysis.competition_simulation import scenario_suite,add_curriculum_exposure

METHOD_VERSION='competition-2026.1'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def code_fingerprint():
    files=[*sorted((ROOT/'analysis').glob('competition_*.py')),ROOT/'agent/competition.py',ROOT/'edumatch/competition_data.py']
    return fingerprint({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


def run_competition(request: dict[str,Any], data: CompetitionData | None=None):
    if not isinstance(request,dict): raise ValueError('请求须为JSON对象')
    data=data or CompetitionData.load(); request=deepcopy(request)
    allowed={'program_id','regions','years','quarter','roles','selected_electives','selected_electives_after','exclude_geography','exclude_cluster',
             'include_preferred','action_candidates','course_budget','allocation','parameters','scenarios'}
    if set(request)-allowed: raise ValueError('未知请求字段: '+','.join(sorted(set(request)-allowed)))
    program=data.program(request.get('program_id','BJUT_SE_2025'))
    request={'program_id':program['id'],'regions':['北京'],'years':[2024,2025],'quarter':None,
        'roles':program['default_role_groups'],'selected_electives':[],'exclude_geography':True,
        'exclude_cluster':False,'include_preferred':True,**request}
    integrity=data.verify()
    if not integrity['ok']: raise ValueError('冻结输入哈希不匹配，请先核验数据：'+str(integrity['mismatches']))
    trace=[{'tool':'verify_inputs','status':'ok','observation':integrity}]
    diagnosis=diagnose(data,request)
    trace.append({'tool':'three_dimension_diagnosis','status':'ok','observation':'技能/方向/规模分列；未知未填0'})
    courses=data.program_courses(program['id']); candidates=request.get('action_candidates',[[]])
    if not isinstance(candidates,list) or not candidates or len(candidates)>3 or any(not isinstance(a,list) or any(not isinstance(x,dict) for x in a) for a in candidates):
        raise ValueError('须提供1—3轮候选动作列表；最多三轮外部评价，不自动编造修订')
    evaluation=None
    revisions: list[dict[str,Any]]=[]
    for i,actions in enumerate(candidates):
        evaluation=evaluate_actions(courses,actions,literature_ids=[r['id'] for r in data.read('literature')],
            skill_ids=[r['id'] for r in data.skills],budget=request.get('course_budget'),
            totals=diagnosis['curriculum_totals'],selected_electives=request['selected_electives'],selected_electives_after=request.get('selected_electives_after'))
        revisions.append({'round':i+1,'actions':actions,'valid':evaluation['valid'],'errors':evaluation['errors']})
        trace.append({'tool':'evaluate_curriculum_constraints','round':i+1,'status':'ok' if evaluation['valid'] else 'rejected','observation':evaluation['errors']})
        if evaluation['valid']: break
    assert evaluation is not None
    accepted_actions=revisions[-1]['actions'] if evaluation['valid'] else []
    proposed_courses=evaluation['courses'] if accepted_actions else []
    proposal_comparison=compare_proposed_path(courses,proposed_courses,request['selected_electives'],
        request.get('selected_electives_after',request['selected_electives']),diagnosis['curriculum_totals'],data.skills,
        diagnosis['skills']['demand']) if accepted_actions else None
    evaluation={k:v for k,v in evaluation.items() if k!='courses'}
    allocation=None
    if request.get('allocation'):
        a=request['allocation']
        if not isinstance(a,dict): raise ValueError('allocation须为JSON对象')
        if a.get('data_status') not in ('synthetic_mechanism_test','user_provided_unverified'): raise ValueError('分流输入必须声明为机制测试或待核实用户数据')
        allocation=allocate_directions(a['students'],a['directions'],seed=a.get('seed',2026),allocation_semester=a.get('allocation_semester'))
        allocation['data_status']=a['data_status']; trace.append({'tool':'deferred_acceptance','status':'ok','observation':allocation['rules_status']})
    plans=diagnosis['scale']['published_plans']; baseline=next((p['published_ordinary_plan_total'] for p in plans if p['year']==2025),None)
    simulation=scenario_suite(baseline,request.get('parameters'),request.get('scenarios'))
    # A teaching schedule is a proposal exposure schedule, not an effect on employment.
    add_curriculum_exposure(simulation,accepted_actions)
    trace.append({'tool':'paired_cohort_scenarios','status':simulation['status'],'observation':'同一外生情景；四年时滞；没有改革就业收益预测'})
    risks=risk_register([a['id'] for a in accepted_actions])
    manifest_hash=fingerprint(data.manifest); implementation=code_fingerprint()
    result={'method_version':METHOD_VERSION,'created_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'request':request,'input_fingerprint':fingerprint({'request':request,'data':manifest_hash,'code':implementation}),
        'data_manifest_hash':manifest_hash,'code_fingerprint':implementation,'diagnosis':diagnosis,
        'curriculum_proposal':evaluation,'proposed_courses':proposed_courses,'proposal_comparison':proposal_comparison,'revision_trace':revisions,'accepted_actions':accepted_actions,'allocation':allocation,
        'simulation':simulation,'risks':risks,'tool_trace':trace,
        'methods':method_cards(data),'sources':{'manifest':data.manifest,'admissions':data.read('admissions')['sources']},
        'limitations':data.manifest['limitations']+['本板块是方法和工具交付；案例课程取舍及真实交互在第四板块确认',
            '已接入EduMatch工具注册表与MCP，支持MCP的助手可调用；本次未调用远程模型，页面查询来自方法卡及计算结果']}
    from analysis.competition_validation import validate_result
    result['validation']=validate_result(result)
    result['result_fingerprint']=fingerprint({k:v for k,v in result.items() if k!='created_at'})
    return result


def method_cards(data):
    refs={r['id']:r for r in data.read('literature')}
    definitions=[
        ('M1','广告技能出现率','含该技能的月度广告数 / 所选有效广告数；一条广告同技能计一次',{'L01':[8,9,12,13],'L02':[6,7,9],'L16':[3,4,5],'L21':[2,4,5]},'词表规则是本项目实现，未经人工金标验证；并非岗位空缺总数'),
        ('M2','严格教学覆盖边界','C充分原文、A完整核查未覆盖、U未知；下界ΣwC，上界Σw(C+U)',{'L15':[4,5,13],'L12':[34,36,42],'L13':[3,4]},'C/A/U及边界是本项目操作化；课名代理不等于掌握或论文原指标'),
        ('M3','方向分配','学生依志愿申请，方向按资格/成绩及公开同分规则暂留至名额',{'L28':[3,5,6]},'稳定是相对给定偏好和优先级，不证明教育公平；容量和制度需核实'),
        ('M4','课程方案外部评价','逐课学分学时、活动守恒、版本、先修和类别约束；最多3轮显式候选',{'L15':[4,5,13],'L25':[2,3],'L17':[2,3,6],'L18':[3,4,9],'L24':[2,8]},'约束检验借鉴优化思想，本实现不是Bertsimas-Sim稳健最优化；不宣称模型自我反思有效'),
        ('M5','年度队列及条件招生反馈','四年队列；毕业次年反馈；死区、连续触发、限幅、平滑和政策边界',{'L39':[2,7,18],'L13':[3,4]},'借鉴反馈时滞原理，不将库存实验系数迁移到招生；未来路径与阈值是可编辑压力假设'),
        ('M6','行动风险与证据强度','风险—行动—后果—知识—责任—触发—响应；未知概率保持null',{'L26':[3,4],'L27':[7,23]},'角色为建议；概率未量化，不能伪装成经验估计'),
    ]
    return [{'id':mid,'name':name,'definition':formula,'support':[{'id':rid,'pdf_pages':pages,'title':refs[rid]['title'],
        'pdf_path':refs[rid]['pdf_path'],'source_url':refs[rid].get('source_url'),'downloaded_version':refs[rid].get('downloaded_version')}
        for rid,pages in citations.items()],'project_adaptation_and_limit':limit} for mid,name,formula,citations,limit in definitions]


def evidence_bundle(result, data=None, skill_id=None):
    data=data or CompetitionData.load()
    rows=result['diagnosis']['skills']['demand']['skills']
    selected=[s for s in rows if skill_id is None or s['skill_id']==skill_id]
    ids={e['ad_id'] for s in selected for e in s['examples']}
    return {'skills':selected,'provenance':data.provenance(ids),'source_row_semantics':'CSV表头之后的记录序号，不是物理换行号；同月单元多来源不重新计数',
            'methods':result['methods'],'admission_sources':result['sources']['admissions']}


def answer_question(question, result):
    """Explicit deterministic query router; never portrays canned answers as LLM inference."""
    if any(w in question for w in ('招生','规模','扩招','情景')):
        payload={'scale':result['diagnosis']['scale'],'simulation':result['simulation']}
        summary='公开招生计划可作情景基期，但实际录取、报到和可新增容量仍未核实。两组使用相同外生信号，四年培养时滞后才进入反馈；这里输出条件人数，不是学校扩招建议或就业预测。'
    elif any(w in question for w in ('课程','学时','改课','教学')):
        payload={'coverage':result['diagnosis']['skills']['strict_coverage'],'proposal':result['curriculum_proposal'],'actions':result['accepted_actions']}
        summary=f"本轮通过编码约束的课程动作有{len(result['accepted_actions'])}项。具体活动学时是待教师审议的预算，文献支持设计原则，不提供这些最优比例。当前版本大纲证据仍缺，课名对应和拟议活动均不能证明学生能力或就业改善。"
    elif any(w in question for w in ('风险','应对')):
        payload=result['risks']; summary='风险按具体动作列后果、触发与应对，未校准的概率保持未知。出现大纲、排课或容量证据缺口时，应保留原课程与原路径，并先核条件。'
    elif any(w in question for w in ('分流','志愿','方向')):
        payload={'directions':result['diagnosis']['directions'],'allocation':result['allocation']}
        summary='方向岗位群可以重叠，广告份额不是招生名额。分流先看资格，再按学生志愿和公开成绩优先序分配；目前示例学生与名额均为模拟，稳定分配不等于已证明公平。'
    elif any(w in question for w in ('依据','论文','方法','为什么')):
        payload=result['methods']; summary='下方方法卡逐项给出公式、原文页码及本项目改写边界。文献支持方法结构；招生限幅、成绩权重和教学时长均是待审参数，不能称为论文验证过的最优值。'
    else:
        summary='可查询技能诊断、课程学时、招生情景、方向分流、风险、方法依据。修改参数请使用设置并重新计算。此入口按主题检索证据，不进行自由模型推理。'
        payload={'message':summary,'skills':result['diagnosis']['skills']['demand']['skills'][:8]}
    return {'question':question,'mode':'deterministic_evidence_query','run_fingerprint':result['result_fingerprint'],'summary':summary,'answer':payload}
