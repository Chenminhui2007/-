"""University-centred replay: explicit agent proposals + executable external checks.

The calling AI authors the candidate decisions. This module never claims to call an LLM.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

from edumatch.competition_data import CompetitionData
from agent.evidence_session import run_diagnosis, append_event, digest
from analysis.evidence_proposals import evaluate_proposal
from analysis.university_scenarios import capacity_stress


VERSION='university-2026.3'


def write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def run_university(brief, output, data=None):
    """Create a new immutable run directory. Reject reuse to preserve prior evidence."""
    data=data or CompetitionData.load()
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('输出目录已有内容，请指定新目录，保留历史运行')
    if brief.get('subject')!='university_program':
        raise ValueError('本流程主体须为高校专业')
    candidates=brief.get('candidates',[])
    if not 1<=len(candidates)<=5:
        raise ValueError('须输入1—5个明确候选；不自动编造模型修订')
    integrity=data.verify()
    if not integrity['ok']: raise ValueError('冻结数据校验失败：'+str(integrity))
    request=deepcopy(brief['request'])
    if request.get('action_candidates') or request.get('allocation'):
        raise ValueError('诊断请求不混入旧候选或学生名单；候选通过独立评价入口')
    output.mkdir(parents=True,exist_ok=True)
    ledger=output/'process/events.jsonl'
    program=data.program(request['program_id'])
    courses=data.program_courses(program['id'])
    totals=[r for r in data.read('curriculum_totals') if r['program_id']==program['id']]
    write_json(output/'inputs/university_brief.json',brief)
    write_json(output/'inputs/data_manifest.json',data.manifest)
    write_json(output/'inputs/courses.json',courses)
    write_json(output/'inputs/task_mapping.json',brief['tasks'])
    append_event(ledger,kind='input',origin='public_document',source=brief['input_provenance'],
        payload={'subject':brief['subject'],'request':request,'data_manifest_hash':digest(data.manifest),
                 'notice':'高校侧公开资料整理输入，不宣称学校直接委托或提交'})
    result=run_diagnosis(request,data=data)
    diagnosis=result['diagnosis']
    scale=diagnosis['scale']
    demand=diagnosis['skills']['demand']
    university_input={
        'program':program,'courses':courses,'curriculum_totals':totals,
        'published_plans':scale['published_plans'],'historical_resources':scale['historical_resources'],
        'historical_outcomes':scale['historical_outcomes'],'sources':brief['evidence_review']['sources'],
        'market_request':result['request'],'course_budget':brief['course_budget'],
    }
    write_json(output/'inputs/university_input.json',university_input)
    if request.get('target_role')=='software_engineer':
        if not demand['n_postings']:
            raise ValueError('所选窗口没有软件工程师招聘样本，请检查职位和时间地域')
        course_lookup={course['course_code']:course for course in courses}
        skill_lookup={skill['skill_id']:skill for skill in demand['skills']}
        rows=[]
        for skill_id,codes,decision,action in brief.get('role_course_mapping',[]):
            if skill_id not in skill_lookup or any(code not in course_lookup for code in codes):
                raise ValueError('职位与课程对照包含未知词项或课程编码')
            signal=skill_lookup[skill_id]
            rows.append({
                'skill_id':skill_id,'skill':signal['skill'],'posting_count':signal['posting_count'],
                'prevalence':signal['prevalence'],'courses':[course_lookup[code] for code in codes],
                'assessment_gap':decision,'action':action,
            })
        diagnosis['role_alignment']={
            'position':'软件工程师','posting_count':demand['n_postings'],
            'company_count':demand['n_company_keys'],'denominator':demand['denominator'],
            'selection':'软件开发岗位群内，匹配职位名“软件工程师”或“软件开发工程师”，排除嵌入式、硬件、测试、算法等专门岗位。',
            'rows':rows,
        }
        result['interaction_result_hash']=digest({k:v for k,v in result.items() if k!='interaction_result_hash'})
    append_event(ledger,kind='input',origin='tool_result',payload={
        'file':'inputs/university_input.json','hash':digest(university_input),
        'courses':len(courses),'position':diagnosis.get('role_alignment',{}).get('position'),
    })
    write_json(output/'results/01_diagnosis.json',result)
    append_event(ledger,kind='diagnosis',origin='tool_result',payload={
        'file':'results/01_diagnosis.json','hash':digest(result),'blockers':result['evidence_gate']})
    evidence_hash=digest(brief['evidence_review'])
    write_json(output/'inputs/evidence_review.json',brief['evidence_review'])
    append_event(ledger,kind='input',origin='public_document',source=brief['evidence_review']['sources'],
        payload={'file':'inputs/evidence_review.json','hash':evidence_hash,'review_scope':'原文定位核读，不是独立专家验证'})
    evaluations=[]; events={}; seen=set()
    for index,candidate in enumerate(candidates,1):
        cid=candidate['id']
        if cid in seen: raise ValueError('候选ID重复')
        seen.add(cid)
        parent=candidate.get('parent')
        if parent and parent not in events: raise ValueError('修订必须引用之前的候选')
        event=append_event(ledger,kind='revision' if parent else 'proposal',origin='agent_proposal',
            payload={'candidate_id':cid,'author':brief['agent_author'],'candidate':candidate},
            parent=events[parent] if parent else None,reason=candidate.get('revision_reason'))
        events[cid]=event['hash']
        evaluation=evaluate_proposal(courses,candidate['actions'],
            literature_ids=brief['literature_ids'],task_ids=[t['id'] for t in brief['tasks']],
            resources=candidate.get('resources'),budget=brief['course_budget'],totals=totals,
            selected_electives=request.get('selected_electives',[]))
        record={'candidate_id':cid,'candidate':candidate,'evaluation':evaluation}
        write_json(output/f'process/{index:02d}_{cid}.json',record)
        append_event(ledger,kind='evaluation',origin='tool_result',parent=event['hash'],payload={
            'candidate_id':cid,'status':evaluation['status'],'errors':evaluation['errors'],
            'evidence_gaps':evaluation['evidence_gaps'],'result_hash':digest(evaluation)})
        evaluations.append(record)
    selected=next((x for x in evaluations if x['candidate_id']==brief['selected_candidate']),None)
    if not selected or not selected['evaluation']['accepted_for_comparison']:
        raise ValueError('选中候选未通过可比较的输入约束')
    decision={'selected_candidate':selected['candidate_id'],'status':selected['evaluation']['status'],
        'rationale':brief['selection_reason'],'institution_approved':False,'implemented':False,
        'directions':brief['directions'],'allocation':{'status':'not_run','reason':'无真实志愿、资格及确认容量，不生成学生名单'},
        'admissions_policy':brief['admissions_policy'],'candidates':evaluations}
    write_json(output/'results/02_proposal.json',decision)
    # Compare only quantities genuinely known on both sides; no fake learning-gain coefficient.
    evaluation=selected['evaluation']
    activity_rows=[]
    for action in selected['candidate']['actions']:
        after=action['outputs'][0]
        before=[c for c in courses if c['course_id'] in action['source_course_ids']]
        activity_rows.append({'action_id':action['id'],'course':after['course_name'],
            'before_credits':sum(c['credits'] for c in before),'after_credits':after['credits'],
            'before_hours':sum(c['hours_total'] for c in before),'after_hours':after['hours_total'],
            'proposed_activities':after['activities'],'verified_learning_gain':None})
    validation={'comparison':activity_rows,'delta':evaluation['curriculum_constraints']['delta'],
        'coverage_gain':None,'employment_gain':None,'reason':'当前教学证据与实施结果不足，不能计算学习或就业提升',
        'simulation':result['simulation'],'capacity_stress':capacity_stress(),
        'learning_validation_plan':brief['learning_validation_plan'],
        'claims':[
            {'claim':'所选候选守住所声明学分学时预算','supported':evaluation['curriculum_constraints']['valid']},
            {'claim':'学校拥有实施余量','supported':None},
            {'claim':'学生独立任务表现改善','supported':None},
            {'claim':'就业结果改善','supported':None}]}
    write_json(output/'results/03_validation.json',validation)
    append_event(ledger,kind='validation',origin='tool_result',payload={
        'file':'results/03_validation.json','hash':digest(validation),'scope':'设计约束与条件情景，未实施'})
    risks=brief['action_risks']
    if len(risks)<3 or any(not r.get('action_ids') or not r.get('trigger') or not r.get('response') for r in risks):
        raise ValueError('至少三项动作关联风险及触发/应对')
    write_json(output/'results/04_risks.json',risks)
    append_event(ledger,kind='risk',origin='agent_proposal',payload={'risks':risks,'probabilities_calibrated':False})
    from reporting.university import render_university
    page=render_university(brief,result,decision,validation,risks,university_input)
    (output/'index.html').write_text(page,encoding='utf-8')
    checks={'status':'passed','subject':'university_program','no_personal_interview':True,
        'selected_constraint_check':evaluation['curriculum_constraints']['valid'],
        'three_scenarios':len(result['simulation']['runs'])>=3,
        'at_least_four_years':all(len(r['rows'])>=4 for r in result['simulation']['runs']),
        'risks':len(risks),'formal_total_score':None,'data_integrity':integrity,
        'numerical_validation':result['validation']}
    write_json(output/'checks.json',checks)
    source_root=Path(__file__).resolve().parents[1]
    code_paths=['agent/university_workflow.py','reporting/university.py','analysis/evidence_proposals.py',
        'analysis/evidence_metrics.py','analysis/competition_metrics.py','analysis/competition_actions.py','analysis/competition_simulation.py','analysis/university_scenarios.py']
    manifest={'version':VERSION,'created_at':datetime.now(timezone.utc).isoformat(),
        'input_hash':digest(brief),'data_hash':digest(data.manifest),'agent_author':brief['agent_author'],
        'execution_mode':'calling_agent_authored_candidates_deterministic_replay_no_remote_llm_call',
        'code_hashes':{p:hashlib.sha256((source_root/p).read_bytes()).hexdigest() for p in code_paths},
        'files':[{'path':p.relative_to(output).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in sorted(output.rglob('*')) if p.is_file()]}
    write_json(output/'run_manifest.json',manifest)
    return {'output':str(output.resolve()),'page':str((output/'index.html').resolve()),
        'selected_candidate':selected['candidate_id'],'status':evaluation['status'],'file_count':len(manifest['files'])+1}
