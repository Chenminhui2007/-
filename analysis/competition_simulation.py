"""Paired cohort stress scenarios. No employment treatment effect is asserted."""
from __future__ import annotations
from math import ceil, floor
from typing import Any
from analysis.competition_actions import number

DEFAULT_PARAMETERS: dict[str,Any]={'start_year':2027,'years':8,'degree_years':4,'employment_target':0.90,
    'deadband':0.03,'smoothing':0.5,'consecutive_triggers':2,'max_step_fraction':0.05,
    'policy_floor_factor':0.7,'policy_ceiling_factor':1.3,'retention':1.0,
    'class_size':30,'module_contact_hours':32,'lab_hours_per_student':16,
    'mentoring_hours_per_student':0.5,'available_teacher_hours':None,'available_lab_seat_hours':None}
DEFAULT_SCENARIOS=[{'name':'保守','demand_index':0.8,'employment_signal':0.80},
    {'name':'基准','demand_index':1.0,'employment_signal':0.90},
    {'name':'积极','demand_index':1.2,'employment_signal':0.96}]


def validate_parameters(p):
    for k in ('start_year','years','degree_years','consecutive_triggers','class_size'):
        if isinstance(p[k],bool) or not isinstance(p[k],int) or p[k]<=0: raise ValueError(k+'须为正整数')
    if not 4<=p['years']<=40 or p['degree_years']!=4: raise ValueError('主案例为四年制，推演须4—40年')
    for k in ('employment_target','deadband','smoothing','max_step_fraction','retention'):
        if not number(p[k]) or not 0<=p[k]<=1: raise ValueError(k+'须在[0,1]内')
    if p['smoothing']==0 or p['max_step_fraction']==0: raise ValueError('平滑与限幅须大于0')
    if not 0<p['policy_floor_factor']<=1<=p['policy_ceiling_factor']: raise ValueError('政策上下界须包含基期计划')
    for k in ('module_contact_hours','lab_hours_per_student','mentoring_hours_per_student'):
        if not number(p[k]) or p[k]<0: raise ValueError(k+'是资源测算系数，须为非负有限数；只有可用容量允许未知')
    for k in ('module_contact_hours','lab_hours_per_student','mentoring_hours_per_student','available_teacher_hours','available_lab_seat_hours'):
        if p[k] is not None and (not number(p[k]) or p[k]<0): raise ValueError(k+'须为非负数或未知')


def update_intake(current, base, demand_index, signal, streak, p):
    low=ceil(base*p['policy_floor_factor']); high=floor(base*p['policy_ceiling_factor'])
    target=max(low,min(high,round(base*demand_index)))
    direction=0
    if signal is not None:
        if signal>p['employment_target']+p['deadband'] and target>current: direction=1
        if signal<p['employment_target']-p['deadband'] and target<current: direction=-1
    streak=(streak+direction if streak*direction>0 else direction) if direction else 0
    proposed=current
    if abs(streak)>=p['consecutive_triggers']:
        limit=max(1,floor(current*p['max_step_fraction']))
        move=min(limit,max(1,round(abs(target-current)*p['smoothing'])))
        proposed=current+direction*min(move,abs(target-current))
    return max(low,min(high,proposed)),streak,target


def simulate_pair(base_plan, scenario, parameters=None):
    p=DEFAULT_PARAMETERS | (parameters or {}); validate_parameters(p)
    if isinstance(base_plan,bool) or not isinstance(base_plan,int) or base_plan<=0: raise ValueError('基期计划须为正整数')
    indices=scenario.get('demand_path',[scenario.get('demand_index',1)]*p['years'])
    signals=scenario.get('employment_path',[scenario.get('employment_signal')]*p['years'])
    if len(indices)!=p['years'] or len(signals)!=p['years']: raise ValueError('情景路径长度必须等于推演年数')
    if any(not number(x) or x<=0 for x in indices) or any(x is not None and (not number(x) or not 0<=x<=1) for x in signals): raise ValueError('情景需求/就业反馈超界')
    rows=[]; cohorts={'baseline':{},'adjusted':{}}; intake=base_plan; streak=0
    for t in range(p['years']):
        year=p['start_year']+t
        # Feedback is available only in the year AFTER the first modelled cohort graduates.
        feedback=signals[t] if t>=p['degree_years'] else None
        intake,streak,target=update_intake(intake,base_plan,indices[t],feedback,streak,p)
        row={'year':year,'demand_index_assumption':indices[t],'employment_feedback_assumption':feedback,
            'observed_employment_rate':None,'assumed_employment_effect_of_reform':None,
            'target_if_signal_allows':target,'consecutive_signal_count':streak,'recommended_intake':None}
        for arm,n in [('baseline',base_plan),('adjusted',intake)]:
            cohorts[arm][year]=n
            stock=sum(size*p['retention']**(year-entry) for entry,size in cohorts[arm].items() if 0<=year-entry<p['degree_years'])
            entry=year-p['degree_years']+1
            grads=cohorts[arm].get(entry)
            grads=grads*p['retention']**(p['degree_years']-1) if grads is not None else None
            teacher=ceil(n/p['class_size'])*p['module_contact_hours']+n*p['mentoring_hours_per_student']
            lab=n*p['lab_hours_per_student']
            capacity=None if p['available_teacher_hours'] is None or p['available_lab_seat_hours'] is None else teacher<=p['available_teacher_hours'] and lab<=p['available_lab_seat_hours']
            row[arm]={'conditional_intake':n,'modelled_new_cohort_stock':stock,'total_in_school':None,
                'modelled_graduates':grads,'graduating_entry_year':entry if grads is not None else None,
                'module_teacher_hours_required':teacher,'module_lab_seat_hours_required':lab,
                'verified_capacity_sufficient':None,'assumed_capacity_sufficient':capacity}
        row['intake_difference']=row['adjusted']['conditional_intake']-base_plan
        row['teacher_hours_difference']=row['adjusted']['module_teacher_hours_required']-row['baseline']['module_teacher_hours_required']
        row['lab_seat_hours_difference']=row['adjusted']['module_lab_seat_hours_required']-row['baseline']['module_lab_seat_hours_required']
        rows.append(row)
    return {'name':scenario['name'],'scenario':scenario,'parameters':p,'rows':rows,'baseline_plan':base_plan,
        'first_modelled_graduation_year':p['start_year']+p['degree_years']-1,
        'first_feedback_year':p['start_year']+p['degree_years'],
        'status':'conditional_stress_simulation_not_prediction',
        'resource_scope':'仅一个假设教学模块所需教师接触/指导工时与实验机位小时，不是全专业总容量',
        'assumptions_note':'除四年学制和已核实2025招生计划外，未来需求、反馈率、阈值、资源系数均为可编辑项目压力参数，不由论文给定',
        'literature':['L39','L13','L25'],'reform_effect_identified':False}


def scenario_suite(base_plan, parameters=None, scenarios=None):
    if base_plan is None: return {'status':'unavailable','reason':'该对照专业没有已核实的招生基准','runs':[],'sensitivity':[]}
    p=DEFAULT_PARAMETERS | (parameters or {}); validate_parameters(p)
    sc=scenarios if scenarios is not None else DEFAULT_SCENARIOS
    if len(sc)<3 or len({s['name'] for s in sc})!=len(sc): raise ValueError('须至少三个不同名称情景')
    runs=[simulate_pair(base_plan,s,p) for s in sc]
    sensitivity=[]
    for step in (0.025,0.05,0.10):
        for smooth in (0.25,0.5,1.0):
            for s in sc:
                r=simulate_pair(base_plan,s,p|{'max_step_fraction':step,'smoothing':smooth})
                sensitivity.append({'scenario':s['name'],'max_step_fraction':step,'smoothing':smooth,
                    'last_conditional_intake':r['rows'][-1]['adjusted']['conditional_intake']})
    probes=[]
    for index,signal in ((0.8,0.8),(1,0.9),(1.2,0.96)):
        current=base_plan; streak=0; values=[]
        for _ in range(60):
            current,streak,target=update_intake(current,base_plan,index,signal,streak,p); values.append(current)
        probes.append({'demand_index':index,'employment_signal':signal,'last_intake':current,'target':target,
            'fixed_last_10':len(set(values[-10:]))==1,'target_reached':current==target,
            'scope':'固定且方向一致的假设反馈、无冲击；数值检验，不是任意市场条件下收敛证明'})
    return {'status':'conditional','runs':runs,'sensitivity':sensitivity,'fixed_signal_checks':probes,
            'real_admission_recommendation':None,'known_existing_cohorts':None}


def add_curriculum_exposure(simulation, actions):
    for run in simulation['runs']:
        for row in run['rows']:
            row['planned_curriculum_exposure']=[{'action_id':a['id'],'first_applicable_entry_year':a['effective_entry_year'],
                'first_teaching_calendar_year':a['effective_entry_year']+o['teaching_year']-1,
                'active_for_new_cohorts':row['year']>=a['effective_entry_year']+o['teaching_year']-1}
                for a in actions for o in a.get('outputs',[])]
    return simulation
