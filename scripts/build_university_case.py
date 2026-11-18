"""Create the calling agent's explicit IMIS case inputs. No personal interaction."""
from pathlib import Path
from copy import deepcopy
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from edumatch.competition_data import CompetitionData
from agent.university_workflow import write_json


def build():
    d=CompetitionData.load();pid='BJUT_IM_2024';lookup={c['course_code']:c for c in d.program_courses(pid)}
    review=ROOT.parent/'output/08_信管证据链核验_20261118'
    tasks=json.loads((review/'六项试点任务_待审映射.json').read_text(encoding='utf-8'))
    sources=json.loads((review/'来源与边界.json').read_text(encoding='utf-8'))['sources']
    supports=[
        {'source_id':'L15','locator':'Biggs1996，PDF4—5、13页','claim':'目标、教学活动与考核对齐；不规定本项目的最优学时','support_reviewed':True},
        {'source_id':'S01','locator':'IS2020，PDF103、107—111、123—124页','claim':'关系查询、业务分析、可视化及系统分析任务框架；本校课程映射为项目操作化','support_reviewed':True},
        {'source_id':'S10','locator':'作者公开稿PDF4—6、10、13页','claim':'区分工具辅助表现与独立表现；高中数学效应数值不迁移到本专业','support_reviewed':True}]
    def action(code,aid,activities,outcome,assessment):
        c=lookup[code]
        out={k:c[k] for k in ['course_id','course_name','credits','hours_total','category','requirement']}
        out.update(activities=activities,learning_outcome=outcome,assessment=assessment,prerequisites=[],teaching_year=4 if code=='0007919' else 3)
        return dict(id=aid,kind='revise',source_course_ids=[c['course_id']],outputs=[out],effective_entry_year=2027,
            rationale='保留现有课程与学分，先完善业务任务—成果—考核追溯。历史大纲已有项目，避免以新课重复替代；实际实施前核对现行大纲、先修及工作量。',
            literature_ids=['L15','S01','S10'],demand_skill_ids=['T1','T2','T3','T4','T5'],
            evidence_support=deepcopy(supports),task_mapping_reviewed=False,
            gap_type='design_traceability_and_evidence_gap_not_proven_student_deficiency',
            prerequisites_review_status='当前先修顺序尚待学院复核；空数组不表示无先修要求')
    bi=[dict(description='商务分析、统计与数据仓库理论及案例',hours=24,skill_ids=['T4'],format='lecture'),
        dict(description='复用既有数据分析项目：取数、处理与业务解释',hours=6,skill_ids=['T2','T3','T5'],format='lab'),
        dict(description='个人关键步骤复现与结果边界说明',hours=2,skill_ids=['T4','T5'],format='lab')]
    practice=[dict(description='业务需求及验收标准追溯',hours=12,skill_ids=['T1'],format='project'),
        dict(description='系统/数据模型与可验证方案',hours=18,skill_ids=['T1','T2'],format='project'),
        dict(description='实现、测试与变更记录',hours=20,skill_ids=['T2','T6'],format='project'),
        dict(description='业务汇报、个人复现与交付复核',hours=10,skill_ids=['T5'],format='project')]
    final=[action('0007919','U01',bi,'围绕业务问题完成数据分析并解释关键操作、结果及限制。','保留项目报告，补关键步骤复现记录与个人贡献证据；评分比例由课程组确认。'),
        action('0002137','U02',practice,'将业务需求、系统模型与验收证据关联，解释一个需求变更的影响。','提交需求—设计—测试追溯表、变更记录及个人说明；现有考核比例先核查。')]
    initial=deepcopy(final)
    initial[0]['outputs'][0]['hours_total']=40
    initial[0]['outputs'][0]['activities'][-1]['hours']=10
    initial[0]['rationale']='初稿在原32学时上追加8学时个人复现与解释训练，以增加检验机会；需接受总量预算与教师工时检查。'
    resources=[dict(id='两门课教师接触与指导工时',demand=102,available=None,unit='教师小时',period='一个30人教学组实施周期',
        assumption='32+60接触工时，加每生20分钟个别复核共10小时；不是全专业总工时，也不是额外增量',source_id=None),
        dict(id='实验与实践机位',demand=2040,available=None,unit='机位小时',period='一个30人教学组实施周期',
        assumption='(商务智能8+系统实践60)*30；每生独占机位为保守压力输入，实际共享方式待核')]
    directions=[
        dict(id='DA',name='商务数据分析',roles='数据分析与工程（较宽岗位族，需逐条复核）',courses=['数据库技术与应用','管理统计学','Python语言','商务智能方法与应用','信息计量学'],
            selection_rule='拟在第4学期末申请；以学生意愿为先，基础课程通过且完成统一试作；超额时按事先公布试作量规排序，同分公开抽签；容量由教师/机位工时核定，未知前不公布配额。'),
        dict(id='IS',name='企业信息系统与流程分析',roles='信息系统与业务（交叉岗位单列）',courses=['管理信息系统','信息系统分析与设计','对应实践','企业资源计划','企业咨询与流程再造','信息系统项目管理'],
            selection_rule='拟在第4学期末申请；意愿与先修通过为资格，统一需求分析试作提供排序依据；容量经学院核定；设转向、补修与申诉窗口。')]
    risks=[
        dict(id='R1',risk='个人复现安排挤占理论或增加负担',action_ids=['U01'],trigger='32学时内无法完成必要主题或额外工作量超过课程组批准预算',response='优先替换重复考核；回退原安排，缩小试点',monitor='每生工作量、主题保留、教师反馈小时',owner='课程组，实施前与每轮项目后',probability=None),
        dict(id='R2',risk='实践重组与原考核或先修要求冲突',action_ids=['U02'],trigger='现行大纲或教师确认关键成果遗漏、先修未满足',response='保留原60学时与原课程；仅补追溯记录，重新审议活动安排',monitor='先修违例、遗漏成果数、验收记录',owner='专业负责人及实践课程组，排课前',probability=None),
        dict(id='R3',risk='师资、机房容量不足',action_ids=['U01','U02','direction_allocation'],trigger='任一可用工时未核实或需求超过同期余量',response='保持条件方案；核实共用占用，分组或降低试点人数',monitor='102教师小时、2040机位小时压力输入与实际余量差',owner='学院与实验中心，试点前',probability=None),
        dict(id='R4',risk='市场样本偏差与四年反馈滞后导致过度调招',action_ids=['admissions_controller'],trigger='雇主集中、窗口结构变化或不同截止日就业信号被混用',response='复核同期和雇主等权；连续信号触发、限幅，必要时冻结调整',monitor='样本集中度、每年人数变化、长周期稳定性',owner='招生与就业部门，每年同一截止日',probability=None),
        dict(id='R5',risk='AI辅助掩盖独立任务能力，或单一考试伤害合理协作',action_ids=['U01','U02'],trigger='项目成绩与独立复现明显不一致；评价申诉或适应困难',response='分别报告工具辅助与独立表现；公开量规、合理支持及复核，不以一次表现推断总体能力',monitor='两类任务差异、复核记录、完成率',owner='课程组，每轮评价后',probability=None)]
    return dict(version='university-2026.3',subject='university_program',agent_author='当前对话Codex：基于已核读文献和本地资料提出显式候选；本脚本不调用远程LLM',
        input_provenance={'mode':'public_sources_reconstructed','school_direct_submission':False,'notice':'公开高校资料与官方脱敏岗位数据整理；不是高校真实委托记录'},
        request=dict(program_id=pid,regions=['北京'],years=[2024,2025],selected_electives=json.loads((ROOT/'data/cases_2026/IM_DATA_CONSERVATIVE.json').read_text(encoding='utf-8'))['selected_electives'],
            parameters={'module_contact_hours':92,'lab_hours_per_student':68,'mentoring_hours_per_student':1/3}),
        tasks=tasks,evidence_review={'sources':sources,'findings':[
            '2020商务智能大纲已有24讲授+8实验与80%项目报告，不能宣称原来无完整项目。',
            '2024表列商务智能32讲课，历史与当前标注有差异，不能认定沿用。',
            '2020数据库表末格合计24与行和48冲突，保留原件，以2024表48为当前总量来源。',
            '六项试点非完整信管量表；课程、招聘任务和层级须复核，当前状态U。']},
        literature_ids=sorted({r['id'] for r in d.read('literature')}|{'S01','S10'}),
        course_budget=dict(credit_delta_min=0,credit_delta_max=0,hour_delta_min=0,hour_delta_max=0),
        candidates=[dict(id='C1',actions=initial,resources=resources,origin='agent_authored_initial'),
            dict(id='C2',parent='C1',revision_reason='初稿多8学时超出零净增预算；将独立复现整合进原32学时，保留24理论和8实验设计，暂停新增课程/合并课程。',actions=final,resources=resources,origin='agent_authored_revision')],
        selected_candidate='C2',selection_reason='C1增加8学时，与已声明的零净增预算冲突。C2在原课内整合考核，保留课程、学分及总学时；历史大纲已有项目，故撤回“从无到有新增完整项目”的论断。容量、现行适用性和教育合理性未核验，C2仅为条件试点方案。',
        course_add_delete_merge={'add_courses':[],'delete_courses':[],'merge_courses':[],
            'reason':'本轮有据的动作是两门既有课内学时和评价修订；新设/删减/合并暂不建议，待必要成果与重复性证据支持。不能把空清单写成已完成增设/删课。',
            'hours_design':'U01原表32讲课，拟24讲课+8实验；U02保留60实践并明确拟议环节。总学时净变化0。'},
        directions=directions,admissions_policy='以2025公开计划30人为情景基期；实际录取与余量未知，不直接扩招。每年同一统计截止日采集同专业毕业去向与对口就业反馈，四年时滞后更新。情景控制用90%目标、3个百分点死区、连续2次触发、5%年限幅、0.5平滑，全部为待审压力参数。资源超限或口径不可比则冻结调整。',
        learning_validation_plan='实施前冻结同难度任务和公开量规，分别记录工具辅助任务与独立复现。先小范围试点，记录基线、对照/分组条件、评分者一致性、完成率与工作量；报告差异及不确定性。没有实施数据前不估计学习或就业提升。',
        action_risks=risks)


if __name__=='__main__':
    dest=ROOT/'data/university_cases/BJUT_IM_2024.json'
    write_json(dest,build());print(str(dest))
