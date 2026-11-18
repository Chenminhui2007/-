"""Auditable diagnostics. All ratios refer to observed advertisements, never vacancies."""
from __future__ import annotations
from collections import Counter, defaultdict
from functools import lru_cache
import math
import re
from statistics import median
from typing import Any

ROLES = ('软件开发', 'AI算法与工程', '数据分析与工程', '信息系统与业务', '测试与质量')
REGIONS = ('北京', '天津', '河北')
SOFTWARE_ENGINEER_TITLE = re.compile(r'软件(?:开发)?工程师', re.I)
SPECIALIZED_SOFTWARE_TITLE = re.compile(r'嵌入式|固件|驱动|硬件|测试|感知|车载|汽车|算法|下位机|通信|存储|仿真')


def matches_software_engineer(title):
    """Match a single recruitment title family within the broader software group."""
    return bool(SOFTWARE_ENGINEER_TITLE.search(title) and not SPECIALIZED_SOFTWARE_TITLE.search(title))


@lru_cache(maxsize=30000)
def _mentions(text: str, patterns: tuple) -> tuple:
    found=[]
    for skill_id, pattern in patterns:
        for m in re.finditer(pattern, text, re.I):
            left=re.split(r'[。；;\n，,]', text[max(0,m.start()-35):m.start()])[-1]
            right=re.split(r'[。；;\n，,]',text[m.end():m.end()+24])[0]
            clause_left=re.split(r'[。；;\n，,]',text[max(0,m.start()-100):m.start()])[-1]
            clause_right=re.split(r'[。；;\n，,]',text[m.end():m.end()+100])[0]
            clause_right=re.split(r'岗位职责|工作职责|任职要求|任职资格|[0-9]+[.、]',clause_right)[0]
            clause=clause_left+m.group()+clause_right
            status='mention'
            if (re.search(r'(?:相关|等|类)专业|专业(?:毕业|应届|\s*$)',clause) and not re.search(r'熟悉|掌握|使用|负责|具备|能够|了解|精通|运用',clause)) or re.search(r'(?:横向|晋升|职业发展|发展通道)\s*[:：].*$',clause_left):
                status='context_only'
            elif re.search(r'无需|不要求|不需要|无须|不涉及|非必需|not required|no need',left,re.I) or re.match(r'\s*(?:(?:经验|能力|技能|基础|知识|技术)\s*)?(?:不要求|不需要|无须|无需|非必需|非必要|not required)',right,re.I):
                status='negated'
            elif re.search(r'优先|加分|最好|preferred|nice.to.have',left+right,re.I): status='preferred'
            elif skill_id in {'r','agent','spark'} and not re.search(r'技术|语言|开发|框架|数据|智能|模型|编程|使用|熟悉|掌握|proficien|program',left+right,re.I): status='ambiguous'
            found.append((skill_id,m.start(),m.end(),m.group(),status,text[max(0,m.start()-35):m.end()+35]))
    return tuple(found)


def extract_mentions(text, skills):
    return [dict(zip(('skill_id','start','end','text','status','context'),v))
            for v in _mentions(text,tuple((s['id'],s['pattern']) for s in skills))]


def select_jobs(jobs, *, regions=('北京',), years=(2024,2025), quarter=None, roles=(),
                geography_flags=(), exclude_geography=True, cluster_flags=(), exclude_cluster=False,
                target_role=None):
    if not regions or set(regions)-set(REGIONS): raise ValueError('地域必须是北京、天津、河北的非空子集')
    if not years or set(years)-{2024,2025,2026}: raise ValueError('年份须在2024—2026之间')
    if quarter not in (None,1,2,3,4): raise ValueError('季度必须为1—4或空')
    if 2026 in years and quarter != 1: raise ValueError('2026仅有一季度，须选择Q1；跨年比较也使用Q1')
    if set(roles)-set(ROLES): raise ValueError('未知岗位群')
    if target_role not in (None,'software_engineer'): raise ValueError('未知目标职位')
    geo={r['month_id'] for r in geography_flags}; cluster={r['month_id'] for r in cluster_flags}
    selected={}
    for j in jobs:
        if j['region'] not in regions or j['year'] not in years: continue
        if quarter and (int(j['month'][5:7])-1)//3+1 != quarter: continue
        if roles and not set(roles).intersection(j['role_groups']): continue
        if target_role=='software_engineer' and not matches_software_engineer(j['title']): continue
        if exclude_geography and j['month_id'] in geo: continue
        if exclude_cluster and j['month_id'] in cluster: continue
        selected.setdefault(j['month_id'],j)
    return list(selected.values())


def demand_summary(jobs, skills, *, employer_equal=False, include_preferred=True):
    companies=Counter(j['company_id'] or j['month_id'] for j in jobs)
    denominator=len(companies) if employer_equal else len(jobs)
    counts=defaultdict(float); raw_counts=Counter(); statuses=Counter(); examples={}
    for j in jobs:
        text=j['title']+'\n'+j['description']
        mentions=extract_mentions(text,skills)
        statuses.update(m['status'] for m in mentions)
        accepted=[m for m in mentions if m['status']=='mention' or (include_preferred and m['status']=='preferred')]
        weight=1/companies[j['company_id'] or j['month_id']] if employer_equal else 1
        for sid in {m['skill_id'] for m in accepted}:
            counts[sid]+=weight; raw_counts[sid]+=1
        for m in mentions:
            key=m['skill_id']
            if len(examples.setdefault(key,[]))<3:
                examples[key].append(dict(m,ad_id=j['ad_id'],month_id=j['month_id'],title=j['title'],region=j['region'],month=j['month']))
    mass=sum(counts.values())
    rows=[{'skill_id':s['id'],'skill':s['name'],'posting_count':raw_counts[s['id']],
           'prevalence':counts[s['id']]/denominator if denominator else None,
           'relative_weight':counts[s['id']]/mass if mass else None,
           'examples':examples.get(s['id'],[])} for s in skills]
    rows.sort(key=lambda r: -(r['prevalence'] or 0))
    salaries=[j['salary_mid'] for j in jobs if j.get('salary_mid') is not None]
    return {'n_postings':len(jobs),'n_company_keys':len(companies),'denominator':denominator,
        'weighting':'employer_equal' if employer_equal else 'posting_equal',
        'unit':'去重月度招聘广告单元','skills':rows,'mention_status_counts':dict(statuses),
        'median_advertised_monthly_midpoint':median(salaries) if salaries else None,
        'salary_n':len(salaries),'salary_is_graduate_income':False,
        'largest_company_share':max(companies.values())/len(jobs) if jobs else None,
        'relative_weight_basis':'归一化技能广告提及量，项目摘要权重；不是熟练度或重要性标定',
        'measurement':'词表候选提及；否定、歧义和已识别专业/晋升背景剔除，优先项可选；未标注背景仍可能残留，无独立人工金标准，准确率未知',
        'literature':['L01','L02','L16','L21','L27','L35']}


TITLE_ALIASES={'statistics':r'统计','data_analysis':r'数据分析|商业数据', 'database':r'数据库',
    'project':r'项目管理','requirements':r'需求分析','testing':r'软件测试',
    'architecture':r'软件体系结构|软件设计与体系结构|软件架构','security':r'信息安全|网络安全',
    'cloud':r'云计算|云原生|云服务','ml':r'机器学习','dl':r'深度学习','knowledge_graph':r'知识图谱'}


def course_path(courses, selected_electives=(), totals=()):
    known={c['course_id']:c for c in courses}; ids=list(selected_electives)
    errors=[]
    if len(set(ids))!=len(ids): errors.append('选修课程ID重复')
    for cid in ids:
        c=known.get(cid)
        if c is None or not c['eligible_for_computation'] or c['requirement']!='elective_pool':
            errors.append('不是本版本可计算的选修课程: '+cid)
    if errors: raise ValueError('；'.join(errors))
    selected=[c for c in courses if c['eligible_for_computation'] and (c['requirement']=='required' or c['course_id'] in ids)]
    minima=[]
    for t in totals:
        if '选修' not in t['label']: continue
        cs=[c for c in selected if c['category']==t['label'] and c['requirement']=='elective_pool']
        credits=sum(c['credits'] or 0 for c in cs); hours=sum(c['hours_total'] or 0 for c in cs)
        minima.append({'category':t['label'],'credits':credits,'hours':hours,'minimum_credits':t['credits'],
                       'minimum_hours':t['hours'],'satisfied':credits >= (t['credits'] or 0) and hours >= (t['hours'] or 0)})
    complete=bool(minima) and all(m['satisfied'] for m in minima)
    return selected, {'selected_electives':ids,'elective_minima':minima,'elective_minima_satisfied':complete,
                     'complete_graduation_path_verified':False,
                     'note':'仅核验可编码课程及已录入选修下限；自主课程、课程块与其他毕业条件仍需核对'}


def title_topics(courses, skills):
    result={s['id']:[] for s in skills}
    for c in courses:
        if not c['eligible_for_computation']: continue
        for s in skills:
            pattern=s['pattern']+'|'+TITLE_ALIASES[s['id']] if s['id'] in TITLE_ALIASES else s['pattern']
            if re.search(pattern,c['course_name'],re.I):
                result[s['id']].append({k:c[k] for k in ('course_id','course_name','requirement','hours_total','credits','source_pdf','pdf_page')})
    return result


def teaching_coverage(program, courses, skills, demand, reviews, source_paths):
    ids={c['course_id'] for c in courses}; states={s['id']:'U' for s in skills}; audit=[]; accepted_states={s['id']:set() for s in skills}
    for r in reviews:
        if r.get('program_id')!=program['id']: continue
        sid=r.get('skill_id'); state=r.get('status')
        valid=(sid in states and r.get('source_pdf') in source_paths and r.get('pdf_page',0)>0 and bool(r.get('reviewer'))
            and r.get('curriculum_year')==program['year'] and r.get('verified_current_version') is True
            and r.get('source_kind') in ('course_syllabus','assessment','teaching_evidence'))
        if state=='C':
            valid=valid and r.get('course_id') in ids and all(r.get(k) for k in ('outcome_quote','activity_quote','assessment_quote'))
        elif state=='A': valid=valid and r.get('full_materials_checked') is True and bool(r.get('absence_rationale'))
        else: valid=False
        audit.append({'evidence':r,'accepted':bool(valid)})
        if valid:
            accepted_states[sid].add(state)
            states[sid]=state if len(accepted_states[sid])==1 else 'U'
            if len(accepted_states[sid])>1: audit[-1]['conflict']=True
    active=[s for s in demand['skills'] if (s['relative_weight'] or 0)>0]
    lower=sum(s['relative_weight'] for s in active if states[s['skill_id']]=='C') if active else None
    upper=sum(s['relative_weight'] for s in active if states[s['skill_id']]!='A') if active else None
    unknown=sum(s['relative_weight'] for s in active if states[s['skill_id']]=='U') if active else None
    return {'states':states,'lower':lower,'upper':upper,'unknown_weight':unknown,
        'point':lower if active and unknown==0 else None,'audit':audit,
        'label':'当前版本教学覆盖的证据识别边界（不是置信区间或学生掌握率）','literature':['L15','L12','L13']}


def diagnose(data, request):
    program=data.program(request['program_id']); courses=data.program_courses(program['id'])
    totals=[r for r in data.read('curriculum_totals') if r['program_id']==program['id']]
    selected,path=course_path(courses,request.get('selected_electives',[]),totals)
    options=dict(regions=tuple(request.get('regions',['北京'])),years=tuple(request.get('years',[2024,2025])),
        quarter=request.get('quarter'),roles=tuple(request.get('roles',program['default_role_groups'])),
        target_role=request.get('target_role'),
        geography_flags=data.read('geography_flags'),cluster_flags=data.read('cluster_flags'),
        exclude_geography=request.get('exclude_geography',True),exclude_cluster=request.get('exclude_cluster',False))
    jobs=select_jobs(data.jobs,**options)
    demand=demand_summary(jobs,data.skills,include_preferred=request.get('include_preferred',True))
    topics=title_topics(selected,data.skills); pool=title_topics([c for c in courses if c['requirement']=='elective_pool'],data.skills)
    proxy=sum((s['relative_weight'] or 0) for s in demand['skills'] if topics[s['skill_id']]) if jobs and any(s['relative_weight'] for s in demand['skills']) else None
    strict=teaching_coverage(program,selected,data.skills,demand,data.read('reviewed_teaching_evidence'),{r['path'] for r in data.manifest['raw_sources']})
    sensitivity={}
    current_preferred=request.get('include_preferred',True)
    for name,overrides,equal,preferred in [('含地域待核',{'exclude_geography':False},False,current_preferred),('雇主等权',{},True,current_preferred),('排除集中簇',{'exclude_cluster':True},False,current_preferred),('剔除优先项',{},False,False)]:
        d=demand_summary(select_jobs(data.jobs,**(options|overrides)),data.skills,employer_equal=equal,include_preferred=preferred)
        sensitivity[name]={'n_postings':d['n_postings'],'denominator':d['denominator'],'skills':[{k:s[k] for k in ('skill_id','prevalence','relative_weight')} for s in d['skills']],
            'title_topic_proxy':sum((s['relative_weight'] or 0) for s in d['skills'] if topics[s['skill_id']]) if any(s['relative_weight'] for s in d['skills']) else None}
    periods=[]
    for year in (2024,2025,2026):
        for quarter in ([None,1] if year<2026 else [1]):
            d=demand_summary(select_jobs(data.jobs,**(options|{'years':(year,),'quarter':quarter})),data.skills,include_preferred=current_preferred)
            periods.append({'year':year,'window':'Q1' if quarter else '全年','n_postings':d['n_postings'],
                            'largest_company_share':d['largest_company_share'],'median_advertised_midpoint':d['median_advertised_monthly_midpoint'],
                            'warning':'广告样本及来源结构变动，不等同于市场总需求增长'})
    all_roles=select_jobs(data.jobs,**(options|{'roles':(),'target_role':None}))
    directions=[]
    for role in options['roles']:
        js=[j for j in all_roles if role in j['role_groups']]
        if options['target_role']=='software_engineer':
            js=[j for j in js if matches_software_engineer(j['title'])]
        ds=demand_summary(js,data.skills,include_preferred=current_preferred)
        directions.append({'role':'软件工程师' if options['target_role']=='software_engineer' else role,'n_postings':len(js),'window_denominator':len(all_roles),'posting_share':len(js)/len(all_roles) if all_roles else None,
            'top_skills':[{k:s[k] for k in ('skill_id','skill','prevalence')} for s in ds['skills'][:8]],
            'course_modules':{s['skill_id']:topics[s['skill_id']] for s in ds['skills'][:8]},'confirmed_seat_capacity':None,
            'note':'岗位群允许重叠，份额不相加；课程模块是课名代理，名额另需学院确认'})
    plans=[r for r in data.read('admissions')['summary'] if r['major']==program['admissions_major']]
    major='软件工程' if program['id'].startswith('BJUT_SE') else program['major']
    return {'program':program,'skills':{'demand':demand,'strict_coverage':strict,'title_topic_proxy':proxy,
        'title_topic_courses':topics,'elective_pool_topics':pool,'path':path,'sensitivity':sensitivity,'periods':periods},
        'directions':directions,'scale':{'published_plans':plans,'actual_admissions':None,'verified_additional_capacity':None,
            'historical_resources':[r for r in data.read('resources') if r['school']==program['school'] and major in r['major']],
            'historical_outcomes':[r for r in data.read('outcomes') if r['school']==program['school'] and r['major']==major],
            'meaning':'招生计划为规模情景起点；广告数量不能直接换算招生缺口'},
        'curriculum_totals':totals,'auxiliary_tsi':{'value':None,'reason':'三维构念缺少完整同口径量化输入，不生成综合分；旧TSI仅在旧模式查阅'},
        'source_job_ids':[j['ad_id'] for j in jobs]}


def compare_proposed_path(courses, proposed_courses, before_ids, after_ids, totals, skills, demand):
    before,before_path=course_path(courses,before_ids,totals)
    after,after_path=course_path(proposed_courses,after_ids,totals)
    rows: list[dict[str,Any]]=[]
    for label,selected,path in [('现行选修路径',before,before_path),('拟议选修路径',after,after_path)]:
        topics=title_topics(selected,skills)
        weights={s['skill_id']:s['relative_weight'] or 0 for s in demand['skills']}
        activity_hours=defaultdict(float)
        for c in selected:
            for sid,h in c.get('allocated_skill_hours',{}).items(): activity_hours[sid]+=h
        rows.append({'path':label,'path_check':path,
            'codable_course_credits':sum(c['credits'] or 0 for c in selected),
            'codable_course_hours':sum(c['hours_total'] or 0 for c in selected),
            'title_topic_proxy':sum(weights[sid] for sid,cs in topics.items() if cs) if sum(weights.values()) else None,
            'planned_activity_skill_hours':dict(activity_hours) if label=='拟议选修路径' else None,
            'planned_activity_demand_weight':sum(weights.get(sid,0) for sid,h in activity_hours.items() if h>0) if label=='拟议选修路径' and sum(weights.values()) else None,
            'verified_learning_attainment':None})
    return {'rows':rows,'credit_delta':rows[1]['codable_course_credits']-rows[0]['codable_course_credits'],
        'hour_delta':rows[1]['codable_course_hours']-rows[0]['codable_course_hours'],
        'interpretation':'只比较相同岗位样本下的课程路径和拟议教学机会。未编码课程块/自主要求另计；现行活动学时未知，不能用0作改善率分母；课名代理变化不是教育效果。'}
