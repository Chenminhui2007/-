"""Self-contained university result page, generated from a single run's artifacts."""
from html import escape


def e(value):
    return escape(str(value))


def pct(value):
    return '未知' if value is None else f'{value:.1%}'


def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+e(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def render_university(brief,result,decision,validation,risks,university_input=None):
    d=result['diagnosis']; skills=d['skills']; dem=skills['demand']; p=d['program']
    alignment=d.get('role_alignment')
    input_content=''
    if university_input:
        rows=university_input['courses']
        input_content=(
            '<p><a href="inputs/university_input.json">打开完整高校输入 JSON ↗</a></p>'+
            table(['年份','公开普通本科招生计划','分省汇总'],[
                [x['year'],x['published_ordinary_plan_total'],x['aggregation']] for x in university_input['published_plans']])+
            '<details><summary>展开 '+e(len(rows))+' 条教学计划课程及原文页码</summary>'+
            table(['课号','课程','类别','学分','学时','原件页码'],[
                [c['course_code'],c['course_name'],c['category'],c['credits'],c['hours_total'],c['pdf_page']] for c in rows])+'</details>'+
            '<details><summary>展开历史在校人数、师资和毕业去向</summary>'+
            table(['学年','历史资源','数量','原件页码'],[
                [x['period'],x['metric'],f"{x['value']} {x['unit']}",x['pdf_page']] for x in university_input['historical_resources']])+
            table(['届次','毕业人数','去向落实率','截止日'],[
                [x['cohort'],x['graduates'],x['destination_rate_pct']+'%',x['cutoff']] for x in university_input['historical_outcomes']])+'</details>'+
            '<details><summary>展开来源原件和核读定位</summary>'+
            table(['来源','存档路径'],[[x['id'],x['path']] for x in university_input['sources']])+'</details>')
    selected=next(x for x in decision['candidates'] if x['candidate_id']==decision['selected_candidate'])
    ev=selected['evaluation']; blocks=[]
    def section(id,title,body):
        blocks.append(f'<section id="{id}"><div class="eyebrow">{e(id.upper())}</div><h2>{e(title)}</h2>{body}</section>')
    section('overview','高校输入与本次结论',
        '<div class="cards">'+''.join(f'<article><span>{e(k)}</span><strong>{e(v)}</strong><small>{e(n)}</small></article>' for k,v,n in [
        ('分析对象',p['major'],p['school']+' · '+str(p['year'])+'版'),('目标职位',alignment['position'] if alignment else '所选岗位群','需求侧对照'),
        ('市场样本',str(dem['n_postings'])+' 月度广告',str(dem['n_company_keys'])+' 个企业键'),('调整方案',decision['selected_candidate'],'课内试点，先复核容量')])+'</div>'+
        '<h3>决策摘要</h3><p>'+e(brief['selection_reason'])+'</p>'+
        table(['输入','内容','边界'],[
            ['培养数据','2024指导性教学计划；2020历史大纲','完整毕业条件、现行大纲适用性未核验'],
            ['市场数据','2024/2025完整年度；2026Q1同期补充','原始广告为入门候选，非全部毕业生可申请'],
            ['招生与资源','官方计划、历史资源及毕业去向','实际录取/报到和新增可用容量未知'],
            ['约束','总学分与总学时净增量为0','本次案例预算']])+input_content)
    comparison=''
    if alignment:
        comparison='<h3 id="role-comparison">信管培养方案与软件工程师对照</h3><p>'+e(alignment['selection'])+'</p>'+table(
            ['职位要求','广告数／出现率','课程计划定位','课程与考核对照','调整动作'],[
                [row['skill'],f"{row['posting_count']} ／ {pct(row['prevalence'])}",
                 '、'.join(f"{c['course_name']}（第{c['pdf_page']}页）" for c in row['courses']),
                 row['assessment_gap'],row['action']] for row in alignment['rows']])
    section('diagnosis','任务1 · 技能、方向、规模三维诊断',
        comparison+'<h3>招聘关键词统计</h3><p>出现率按目标职位广告计算。同一广告每个词项计一次，课程考核另核对。</p>'+
        table(['词项','广告数','出现率'],[[s['skill'],s['posting_count'],pct(s['prevalence'])] for s in dem['skills'][:12]])+
        '<h3>六项任务与课程证据</h3>'+table(['任务','定义','课程线索','当前状态'],[
        [t['id'],t['definition'],'、'.join(c['course_name'] for c in t['course_candidates']),'U：版本/任务层次/完整路径待核'] for t in brief['tasks']])+
        '<p>U表示证据未识别，不表示学校未教或学生能力为零。正式教学覆盖暂不计算；不将六项试点当完整专业量表。</p>'+
        '<h3>方向岗位与计划规模</h3>'+table(['岗位群','月度广告','共同窗口分母','样本份额'],[
            [x['role'],x['n_postings'],x['window_denominator'],pct(x['posting_share'])] for x in d['directions']])+
        '<p>分母为同地域、时间与筛选条件下所有候选广告；岗位群可交叉，份额不能转成分流配额。</p>'+
        table(['年份','官方普通本科计划','实际录取/报到','新增容量'],[
            [x['year'],x['published_ordinary_plan_total'],'未知','未知'] for x in d['scale']['published_plans']])+
        '<h3>数据口径敏感性</h3>'+table(['处理','样本数','课名主题代理'],[
            [name,x['n_postings'],pct(x['title_topic_proxy'])] for name,x in skills['sensitivity'].items()])+
        '<p>课名主题代理仅检查文本对应，不是培养匹配率。不同年度与Q1样本量、集中度详见JSON。</p>')
    content='<h3>候选比较与修订</h3>'+table(['候选','结论','失败/缺项'],[
        [x['candidate_id'],x['evaluation']['status'],'；'.join(x['evaluation']['errors']+x['evaluation']['evidence_gaps'])] for x in decision['candidates']])
    for a in selected['candidate']['actions']:
        o=a['outputs'][0]
        content+=f'<div class="action"><h3>{e(a["id"])} · {e(o["course_name"])}</h3><p>{e(a["rationale"])}</p><p><b>目标：</b>{e(o["learning_outcome"])}</p><p><b>考核：</b>{e(o["assessment"])}</p>'
        content+=table(['活动','拟议学时','任务'],[[x['description'],x['hours'],'、'.join(x['skill_ids'])] for x in o['activities']])
        content+='<details><summary>查看原文依据及支持边界</summary>'+table(['来源','位置','支持的原则'],[
            [s['source_id'],s['locator'],s['claim']] for s in a['evidence_support']])+'</details></div>'
    content+='<h3>方向与分流规则</h3>'+table(['方向','目标岗位','课程模块','分流条件'],[
        [x['name'],x['roles'],'、'.join(x['courses']),x['selection_rule']] for x in decision['directions']])
    content+='<p>本轮没有真实志愿与确认容量，不生成分流名单；原分配算法作为后续工具保留。</p><h3>招生反馈机制</h3><p>'+e(decision['admissions_policy'])+'</p>'
    content+='<h3>新增、删减、合并与学时决定</h3><p>'+e(brief['course_add_delete_merge']['reason'])+'</p><p>'+e(brief['course_add_delete_merge']['hours_design'])+'</p>'
    section('proposal','任务2 · 课程、方向与招生调整',content)
    endpoints=[(run['name'],run['rows'][-1]) for run in validation['simulation']['runs']]
    content='<h3>如果不调整，招生计划如何变化</h3><p>固定计划与反馈规则使用相同外部情景，比较2034年与设定需求目标的差额。</p>'+table(
        ['情景','设定目标','固定计划','采用反馈规则','距目标差额'],[
            [name,r['target_if_signal_allows'],r['baseline']['conditional_intake'],r['adjusted']['conditional_intake'],
             f"{abs(r['baseline']['conditional_intake']-r['target_if_signal_allows'])} → {abs(r['adjusted']['conditional_intake']-r['target_if_signal_allows'])}"]
            for name,r in endpoints if r['target_if_signal_allows'] is not None])
    content+='<h3>课程学分与学时对照</h3>'+table(['动作','课程','原学分→拟议','原学时→拟议','试点效果'],[
        [x['action_id'],x['course'],f'{x["before_credits"]} → {x["after_credits"]}',f'{x["before_hours"]} → {x["after_hours"]}','未识别'] for x in validation['comparison']])
    content+='<h3>资源条件</h3>'+table(['资源','期间','需求','可用量','状态'],[
        [r['id'],r['period'],f'{r["demand"]} {r["unit"]}','未知' if r['available'] is None else r['available'],r['status']] for r in ev['resource_pressure']])
    content+='<h3>三情景 · 调整与不调整使用相同外生信号</h3><p>以下需求、反馈率与资源系数为显式压力假设，不是市场预测或文献最优参数。点击选择情景。</p><div class="buttons">'
    for i,run in enumerate(validation['simulation']['runs']):content+=f'<button class="scenario-button {"active" if i==0 else ""}" data-target="scenario{i}">{e(run["name"])}</button>'
    content+='</div>'
    for i,run in enumerate(validation['simulation']['runs']):
        content+=f'<div class="scenario" id="scenario{i}" {"hidden" if i else ""}>'
        content+='<p>'+e(run['assumptions_note'])+'</p>'+table(['年份','不调整计划基线','条件调整人数','拟议模块教师工时','机位小时','已证实容量'],[
            [r['year'],r['baseline']['conditional_intake'],r['adjusted']['conditional_intake'],r['adjusted']['module_teacher_hours_required'],r['adjusted']['module_lab_seat_hours_required'],'未知'] for r in run['rows']])+'</div>'
    stress=validation['capacity_stress']
    content+='<h3>与课程动作直接关联的三种资源压力情景</h3><p>以下容量为项目压力输入，未核实本校拥有。C2较被否决的C1在30人组减少8教师接触小时、240机位小时；这不是相对原培养方案的实际节约。资源不足时缩小试点。</p>'
    content+=table(['情景','假设教师余量','假设机位余量','C1教师/机位缺口','C2教师/机位缺口','容量门槛后试点人数'],[
        [x['scenario'],x['assumed_available_teacher_hours'],x['assumed_available_lab_seat_hours'],f'{x["initial_teacher_shortfall"]:.1f} / {x["initial_lab_shortfall"]}',f'{x["final_teacher_shortfall"]:.1f} / {x["final_lab_shortfall"]}',x['gated_pilot_size']] for x in stress['rows']])
    content+='<p>资源模型含30人班额的阶梯效应；31人不等于30人的线性放大。规模由条件可行上界约束，不给市场最优招生结论。</p>'
    content+='<h3>后续实施验证设计</h3><p>'+e(validation['learning_validation_plan'])+'</p>'
    section('validation','任务3 · 反事实对比与实施条件',content)
    section('risks','任务4 · 与动作绑定的风险及回退',table(['风险','关联动作','触发','应对','监测'],[
        [r['risk'],'、'.join(r['action_ids']),r['trigger'],r['response'],r['monitor']] for r in risks])+
        '<p>发生概率缺乏校准数据，保持未知。责任角色为建议，不代表已取得学校授权。</p>')
    section('process','过程记录与可复现材料',
        '<ol><li>冻结高校任务包、课程、数据清单和原文核读记录。</li><li>运行三维诊断并保留输入指纹。</li><li>记录Agent候选、工具错误和缺项。</li><li>根据反馈修订，保留父方案和原因。</li><li>运行前后对照、三情景和风险检查。</li><li>导出本网页、JSON结果、日志与文件哈希。</li></ol>'+
        '<p>本次候选由当前对话中的Codex提出；本地插件执行确定性计算与重放，未在脚本内部调用远程大模型。过程记录不包含模型内部思维。</p>'+
        '<div class="links">'+''.join(f'<a href="{path}">{label} ↗</a>' for path,label in [
            ('inputs/university_brief.json','高校输入任务包'),('results/01_diagnosis.json','三维完整结果'),('results/02_proposal.json','方案与评价'),
            ('results/03_validation.json','验证与情景'),('results/04_risks.json','风险表'),('process/events.jsonl','过程日志'),('run_manifest.json','版本与哈希'),('checks.json','运行检查')])+'</div>')
    nav=''.join(f'<a href="#{k}">{label}</a>' for k,label in [('overview','输入与结论'),('diagnosis','现状诊断'),('proposal','调整方案'),('validation','效果验证'),('risks','风险应对'),('process','过程材料')])
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EduMatch · 高校专业调整分析</title><style>
    :root{--navy:#122c4a;--cyan:#007f91;--line:#dbe5ee;--muted:#5c7185}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f7fb;color:var(--navy);font:16px/1.75 'Microsoft YaHei','Segoe UI',sans-serif}header{background:var(--navy);color:white;padding:38px max(5vw,24px)}header p{color:#c4d9ea;margin:0}h1{font-size:34px;line-height:1.4;max-width:1050px;margin:12px 0}nav{position:sticky;top:0;background:#ffffffed;backdrop-filter:blur(8px);border-bottom:1px solid var(--line);display:flex;gap:24px;padding:14px 5vw;overflow:auto;z-index:2}a{color:var(--cyan);text-decoration:none}nav a{white-space:nowrap;font-weight:600}main{max-width:1240px;margin:auto;padding:25px}section{background:white;border:1px solid var(--line);border-radius:12px;padding:28px;margin:20px 0;scroll-margin-top:75px}.eyebrow{color:var(--cyan);letter-spacing:2px;font-size:12px;font-weight:700}h2{font-size:25px;margin:5px 0 22px}h3{margin-top:28px;font-size:19px}.notice{background:#fff5de;border-left:4px solid #c98d13;padding:14px 18px;color:#68501d}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}.cards article{padding:18px;background:#edf6fb;border-radius:8px}.cards span,.cards small{display:block;color:var(--muted);font-size:12px}.cards strong{font-size:23px;display:block;line-height:1.4;margin:9px 0}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px;margin:16px 0}th{text-align:left;background:#edf3f8;color:#31536f;white-space:nowrap}td,th{padding:13px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:hover{background:#f6fafc}.action{border-left:3px solid var(--cyan);padding:0 0 8px 20px;margin:25px 0}summary{cursor:pointer;color:var(--cyan)}button{border:1px solid var(--cyan);color:var(--cyan);background:white;border-radius:5px;padding:9px 24px;font:inherit;cursor:pointer}.buttons{display:flex;gap:12px}button.active{background:var(--cyan);color:white}.links{display:flex;gap:12px;flex-wrap:wrap}.links a{padding:10px 14px;border:1px solid var(--line);border-radius:5px}footer{padding:25px;text-align:center;color:var(--muted);font-size:13px}@media(max-width:750px){.cards{grid-template-columns:repeat(2,1fr)}main{padding:10px}section{padding:17px}h1{font-size:26px}}@media print{nav,.buttons{display:none}.scenario[hidden]{display:block}section{break-inside:auto;border:0}body{background:white}.scroll{overflow:visible}}
    </style><header><p>EDUMATCH / UNIVERSITY DECISION SUPPORT / 2026.3</p><h1>北京工业大学 · 信息管理与信息系统<br>从专业数据到可审议的调整方案</h1><p>高校专业为主体 · 证据约束 · 有限迭代 · 全过程留痕</p></header><nav>'''+nav+'</nav><main>'+''.join(blocks)+'''</main><footer>本地单文件结果网页 · 详细输入与计算结果随运行目录保留 · 尚未实施的高校专业调整研究方案</footer><script>
    document.querySelectorAll('.scenario-button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.scenario').forEach(x=>x.hidden=x.id!==b.dataset.target);document.querySelectorAll('.scenario-button').forEach(x=>x.classList.toggle('active',x===b));}));
    </script></html>'''
