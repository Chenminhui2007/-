"""Constraint checks and student-proposing allocation; no fabricated school rules."""
from __future__ import annotations
from copy import deepcopy
from collections import deque
import hashlib
import math


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def evaluate_actions(courses, actions, *, literature_ids=(), skill_ids=(), budget=None, totals=(), selected_electives=(), selected_electives_after=None):
    """Apply a complete proposal atomically only after all constraints pass."""
    budget=budget or {'credit_delta_min':0,'credit_delta_max':0,'hour_delta_min':0,'hour_delta_max':0}
    original={c['course_id']:deepcopy(c) for c in courses}; working=deepcopy(original)
    errors=[]; warnings=[]; touched=set(); action_ids=set(); net_delta={'credits':0.0,'hours_total':0.0}; comparisons=[]
    if not original: raise ValueError('课程集为空')
    program_ids={c['program_id'] for c in courses}
    if len(program_ids)!=1: raise ValueError('不能拼接不同培养方案版本')
    pid=next(iter(program_ids))
    for action in actions:
        aid=action.get('id'); kind=action.get('kind'); sources=action.get('source_course_ids',[]); outputs=action.get('outputs',[])
        if not aid or aid in action_ids: errors.append('动作ID缺失或重复')
        action_ids.add(aid)
        if kind not in ('add','delete','merge','revise'): errors.append(f'{aid}: 未知动作类型'); continue
        if (kind=='add' and sources) or (kind in ('delete','revise') and len(sources)!=1) or (kind=='merge' and len(sources)<2): errors.append(f'{aid}: 来源课程数量不合法')
        if (kind=='delete' and outputs) or (kind!='delete' and len(outputs)!=1): errors.append(f'{aid}: 输出课程数量不合法')
        valid_sources=[]
        for cid in sources:
            if cid not in original or not original[cid]['eligible_for_computation']: errors.append(f'{aid}: 未知、冲突或不可计算课程 {cid}'); continue
            if cid in touched: errors.append(f'{aid}: 来源课程被重复使用 {cid}')
            touched.add(cid); valid_sources.append(original[cid])
        if any(c['hours_total'] is None or c['credits'] is None for c in valid_sources): errors.append(f'{aid}: 缺学时或学分，不能自动换算周数')
        protected=[c for c in valid_sources if c['requirement']=='required']
        # Without an approved subject classification, protect every required course against reductions.
        if protected and (kind in ('delete','merge') or any((o.get('credits',-1)<c['credits'] or o.get('hours_total',-1)<c['hours_total']) for c in protected for o in outputs if all(number(v) for v in (o.get('credits'),o.get('hours_total'),c['credits'],c['hours_total'])))):
            errors.append(f'{aid}: 必修课程删除、合并或缩减须先获得课程类别和培养约束复核，当前禁止')
        if not action.get('rationale') or not action.get('literature_ids') or set(action.get('literature_ids',[]))-set(literature_ids): errors.append(f'{aid}: 缺有效文献依据与理由')
        if not action.get('demand_skill_ids') or set(action.get('demand_skill_ids',[]))-set(skill_ids): errors.append(f'{aid}: 缺有效需求技能定位')
        if not isinstance(action.get('effective_entry_year'),int): errors.append(f'{aid}: 缺适用入学年份')
        before={k:sum(c[k] or 0 for c in valid_sources) for k in net_delta}; after={k:0.0 for k in net_delta}
        for o in outputs:
            oid=o.get('course_id','')
            if not oid.startswith(pid+':') or (oid in original and oid not in sources) or oid in (set(working)-set(original)): errors.append(f'{aid}: 输出ID跨版本或重名')
            if not all(number(o.get(k)) and o[k]>=0 for k in net_delta): errors.append(f'{aid}: 学分/学时须为非负有限数'); continue
            if o.get('requirement') not in ('required','elective_pool','autonomous'): errors.append(f'{aid}: 修读性质未知')
            if not o.get('course_name') or not o.get('category'): errors.append(f'{aid}: 缺课程名称/类别')
            if isinstance(o.get('teaching_year'),bool) or o.get('teaching_year') not in (1,2,3,4): errors.append(f'{aid}: 须声明拟议教学年级1—4')
            if valid_sources and any(c['requirement']!=o.get('requirement') or c['category']!=o.get('category') for c in valid_sources): errors.append(f'{aid}: 不得静默改变课程类别或修读性质')
            for key in ('learning_outcome','assessment','activities'): 
                if not o.get(key): errors.append(f'{aid}: 缺{key}')
            activities=o.get('activities',[])
            if any(not number(a.get('hours')) or a['hours']<0 or not a.get('description') or set(a.get('skill_ids',[]))-set(skill_ids) for a in activities): errors.append(f'{aid}: 活动学时或技能ID无效')
            elif abs(sum(a['hours'] for a in activities)-o['hours_total'])>1e-8: errors.append(f'{aid}: 教学活动学时必须与课程总学时守恒')
            # Shared activity time is allocated once across skills, not counted in full for each skill.
            allocated={}
            for a in activities:
                ids=list(dict.fromkeys(a.get('skill_ids',[])))
                if number(a.get('hours')):
                    for sid in ids: allocated[sid]=allocated.get(sid,0)+a['hours']/len(ids)
            for k in net_delta: after[k]+=o[k]
            row=deepcopy(o); row.update(program_id=pid,eligible_for_computation=True,source_pdf=None,pdf_page=None,
                evidence_status='proposed_not_implemented',allocated_skill_hours=allocated,learning_attainment=None)
            working[oid]=row
        for cid in sources:
            if cid not in [o.get('course_id') for o in outputs]: working.pop(cid,None)
        delta={k:after[k]-before[k] for k in net_delta}
        for k in net_delta: net_delta[k]+=delta[k]
        comparisons.append({'action_id':aid,'kind':kind,'source_course_ids':sources,'before':before,'after':after,'delta':delta})
    for c in working.values():
        for pre in c.get('prerequisites',[]):
            if pre not in working or pre==c['course_id']: errors.append('先修课程不存在或自依赖: '+c['course_id'])
    graph={c['course_id']:c.get('prerequisites',[]) for c in working.values()}; visiting=set(); visited=set()
    def visit(node):
        if node in visiting: return False
        if node in visited: return True
        visiting.add(node)
        ok=all(visit(x) for x in graph.get(node,[]))
        visiting.remove(node); visited.add(node); return ok
    if any(not visit(n) for n in graph): errors.append('先修关系含循环')
    pool_checks=[]; path_check=None
    if actions:
        from analysis.competition_metrics import course_path
        for t in totals:
            if '选修' not in t['label']: continue
            pool=[c for c in working.values() if c.get('eligible_for_computation') and c['requirement']=='elective_pool' and c['category']==t['label']]
            credits=sum(c['credits'] or 0 for c in pool); hours=sum(c['hours_total'] or 0 for c in pool)
            adequate=credits >= (t['credits'] or 0) and hours >= (t['hours'] or 0)
            pool_checks.append({'category':t['label'],'pool_credits':credits,'pool_hours':hours,'minimum_credits':t['credits'],'minimum_hours':t['hours'],'satisfied':adequate})
            if not adequate: errors.append('修改后选修池不能满足培养方案下限: '+t['label'])
        try:
            after_ids=selected_electives if selected_electives_after is None else selected_electives_after
            _,path_check=course_path(list(working.values()),after_ids,totals)
            _,old_path=course_path(courses,selected_electives,totals)
            if old_path['elective_minima_satisfied'] and not path_check['elective_minima_satisfied']:
                errors.append('修改破坏了已满足下限的选修路径')
        except ValueError as exc: errors.append('修改后选修路径无效: '+str(exc))
    for k,stem in [('credits','credit'),('hours_total','hour')]:
        lo=budget.get(stem+'_delta_min',0); hi=budget.get(stem+'_delta_max',0)
        if not number(lo) or not number(hi) or lo>hi: raise ValueError('课程预算边界无效')
        if not lo-1e-8<=net_delta[k]<=hi+1e-8: errors.append(f'课程总量变化超出已声明预算: {k}={net_delta[k]}')
    if actions: warnings.append('通过表示输入约束自洽；课程内容、认证要求、教师与审批仍需学院复核，不能称已实施')
    planned={}
    if not errors:
        for c in working.values():
            for sid,hours in c.get('allocated_skill_hours',{}).items(): planned[sid]=planned.get(sid,0)+hours
    return {'valid':not errors,'errors':list(dict.fromkeys(errors)),'warnings':warnings,'comparisons':comparisons,
        'proposed_activity_skill_hours':planned,'before_verified_skill_hours':None,
        'activity_hours_note':'共享活动学时在技能间等分，保证只计一次；这是拟议教学安排，不是已验证掌握，也不能用未知基线算提升率',
        'elective_pool_checks':pool_checks,'proposed_path_check':path_check,
        'delta':net_delta,'budget':budget,'courses':list(working.values()) if not errors else courses,
        'status':'constraint_consistent_proposal' if actions and not errors else ('no_proposal' if not actions else 'rejected'),
        'literature':['L15','L25'],'implemented':False}


def allocate_directions(students, directions, *, seed=2026, allocation_semester=None):
    """Student-proposing deferred acceptance, fixed public priorities with deterministic ties."""
    dmap={d['id']:d for d in directions}; smap={s['id']:s for s in students}
    if len(dmap)!=len(directions) or len(smap)!=len(students): raise ValueError('学生/方向ID重复')
    if not directions: raise ValueError('至少一个方向')
    for d in directions:
        if isinstance(d.get('capacity'),bool) or not isinstance(d.get('capacity'),int) or d['capacity']<0: raise ValueError('名额必须是非负整数，未知名额不能填0')
        if not number(d.get('minimum_score')): raise ValueError('须明确拟议资格门槛')
    for s in students:
        prefs=s.get('preferences',[])
        if len(set(prefs))!=len(prefs) or set(prefs)-set(dmap): raise ValueError('志愿含重复或未知方向')
        if any(not number(s.get('scores',{}).get(d)) for d in prefs): raise ValueError('志愿方向缺可核验成绩')
    def eligible(s,d): return s['scores'][d]>=dmap[d]['minimum_score'] and d in s.get('eligible_directions',[])
    def priority(sid,d):
        tie=hashlib.sha256(f'{seed}:{sid}:{d}'.encode()).hexdigest()
        return (-smap[sid]['scores'][d],tie,sid)
    held={d:[] for d in dmap}; next_index={s:0 for s in smap}; queue=deque(sorted(smap)); proposals=[]
    while queue:
        sid=queue.popleft(); s=smap[sid]
        if next_index[sid]>=len(s['preferences']): continue
        d=s['preferences'][next_index[sid]]; next_index[sid]+=1
        if not eligible(s,d): proposals.append({'student_id':sid,'direction':d,'status':'ineligible'}); queue.append(sid); continue
        candidates=sorted(held[d]+[sid],key=lambda x:priority(x,d)); held[d]=candidates[:dmap[d]['capacity']]
        for rejected in candidates[dmap[d]['capacity']:]: queue.append(rejected)
        proposals.append({'student_id':sid,'direction':d,'status':'held' if sid in held[d] else 'rejected'})
    assigned={sid:d for d,ids in held.items() for sid in ids}; blocking=[]
    for s in students:
        prefs=s['preferences']; current=assigned.get(s['id']); preferred=prefs[:prefs.index(current)] if current else prefs
        for d in preferred:
            if eligible(s,d) and (len(held[d])<dmap[d]['capacity'] or any(priority(s['id'],d)<priority(x,d) for x in held[d])): blocking.append([s['id'],d])
    return {'assignments':assigned,'unmatched':[{'student_id':s['id'],'reason':'无志愿、未达到资格或志愿名额被更高优先级占用'} for s in students if s['id'] not in assigned],
        'held':held,'blocking_pairs':blocking,'stable':not blocking,'trace':proposals,'seed':seed,
        'allocation_semester':allocation_semester,'priority':'方向成绩降序；同分SHA256(seed:student:direction)升序',
        'rules_status':'用户输入的拟议机制，非已核实学校制度','literature':['L28'],'fairness_proven':False}


def risk_register(action_ids):
    common={'probability':None,'probability_basis':'无频率样本或专家校准，概率未知','owner_status':'建议责任角色'}
    return [dict(common,id='R1',action_ids=list(action_ids) or ['curriculum_proposal_pending'],risk='新增主题挤占基础训练或考核无法验证学习成果',
        impact='必修学分、活动学时或课程达成度受损',owner='专业负责人和课程组',time='实施前审议与每学期末',trigger='总学分/学时越界或目标—活动—考核任一缺失',response='阻止发布；回到源课程逐项复核，先小班试点'),
        dict(common,id='R2',action_ids=['direction_allocation'],risk='方向名额与志愿冲突、同分规则不透明',impact='学生未分配或申诉',owner='学院教学委员会',time='分流前公示与结果公布后复核',trigger='容量超限、阻塞对存在、资格/成绩缺失',response='冻结分配；核验名单、名额、成绩与同分种子，保留申诉'),
        dict(common,id='R3',action_ids=['conditional_admissions_controller'],risk='广告样本偏差与四年培养时滞造成规模调整过度',impact='新增队列教学负担或毕业供需失衡，人数见情景表',owner='招生与就业部门',time='每年更新；首届改革队列毕业后才反馈',trigger='集中企业份额超过50%或两次反馈越过情景阈值',response='检查雇主等权与去簇结果，限幅、暂停扩张并核查真实就业口径'),
        dict(common,id='R4',action_ids=['conditional_admissions_controller']+list(action_ids),risk='师资、机房或GPU可用容量未证实',impact='课程排课和实验无法兑现',owner='学院与实验中心',time='提出招生/课程变更前',trigger='任一所需容量缺失或需求超过核定上限',response='仅保留条件方案；核验教师工时、开放机时、共享和第二学位占用后再决策')]
