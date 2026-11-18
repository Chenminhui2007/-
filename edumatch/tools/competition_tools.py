"""Frozen competition tools; deliberately independent of legacy Dataset.build()."""
from functools import lru_cache
from edumatch.competition_data import CompetitionData


@lru_cache(maxsize=1)
def data(): return CompetitionData.load()


def run(_ds,args):
    from agent.competition import run_competition
    return run_competition(args.get('request',{}),data())


def evidence(_ds,args):
    from agent.competition import run_competition,evidence_bundle
    return evidence_bundle(run_competition(args.get('request',{}),data()),data(),args.get('skill_id'))


def evaluate(_ds,args):
    from analysis.competition_actions import evaluate_actions
    d=data()
    return evaluate_actions(d.program_courses(args['program_id']),args['actions'],
        literature_ids=[x['id'] for x in d.read('literature')],skill_ids=[x['id'] for x in d.skills],budget=args.get('budget'),
        totals=[r for r in d.read('curriculum_totals') if r['program_id']==args['program_id']],selected_electives=args.get('selected_electives',[]),selected_electives_after=args.get('selected_electives_after'))


def specs():
    from .registry import ToolSpec
    request={'type':'object','description':'program_id, regions, years, quarter, roles, selected_electives, action_candidates, allocation, parameters, scenarios；2026必须Q1'}
    return [ToolSpec('competition_run','competition','按校赛四任务生成三维诊断、约束评价、条件队列情景与风险；真实/计划/假设分列',
        {'type':'object','properties':{'request':request},'additionalProperties':False},run,requires_dataset=False),
        ToolSpec('competition_evidence','competition','追溯技能原句、月度单元全部来源行和方法PDF页码',
        {'type':'object','properties':{'request':request,'skill_id':{'type':'string'}},'additionalProperties':False},evidence,requires_dataset=False),
        ToolSpec('competition_evaluate_actions','competition','核验课程增删合并修订的版本、学时学分、先修、目标活动考核与依据',
        {'type':'object','properties':{'program_id':{'type':'string'},'actions':{'type':'array','items':{'type':'object'}},'budget':{'type':'object'},'selected_electives':{'type':'array','items':{'type':'string'}},'selected_electives_after':{'type':'array','items':{'type':'string'}}},'required':['program_id','actions'],'additionalProperties':False},evaluate,requires_dataset=False)]
