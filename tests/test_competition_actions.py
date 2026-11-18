from copy import deepcopy
import pytest
from analysis.competition_actions import evaluate_actions, allocate_directions


def fixture():
    c={'course_id':'P:c','program_id':'P','course_name':'Python','category':'专业选修课','requirement':'elective_pool','credits':2,'hours_total':32,'eligible_for_computation':True}
    o=dict(c,learning_outcome='实现可复现数据处理',assessment='代码、实验记录与口试',activities=[{'description':'数据处理实验','hours':16,'skill_ids':['python','sql']},{'description':'理论与复核','hours':16,'skill_ids':[]}],prerequisites=[],teaching_year=3)
    a={'id':'A1','kind':'revise','source_course_ids':['P:c'],'outputs':[o],'rationale':'强化可核验实践','literature_ids':['L15'],'demand_skill_ids':['python'],'effective_entry_year':2027}
    return [c],[a]


def evaluate(c,a): return evaluate_actions(c,a,literature_ids=['L15'],skill_ids=['python','sql'])


def test_valid_action_conserves_hours_and_is_not_implemented():
    c,a=fixture(); r=evaluate(c,a)
    assert r['valid'] and r['delta']=={'credits':0,'hours_total':0} and not r['implemented']
    assert r['courses'][0]['allocated_skill_hours']=={'python':8,'sql':8}


@pytest.mark.parametrize('mutation',[
    lambda a:a[0]['outputs'][0].update(hours_total=-1),
    lambda a:a[0]['outputs'][0].update(credits=float('nan')),
    lambda a:a[0]['outputs'][0].update(course_id='OTHER:c'),
    lambda a:a[0]['outputs'][0].update(assessment=''),
    lambda a:a[0]['outputs'][0].update(prerequisites=['P:c']),
    lambda a:a[0]['outputs'][0]['activities'][0].update(hours=30),
    lambda a:a[0].update(literature_ids=['invented']),
    lambda a:a[0].update(source_course_ids=['P:missing']),
])
def test_reject_invalid_action_atomically(mutation):
    c,a=fixture(); mutation(a); r=evaluate(c,a)
    assert not r['valid'] and r['courses']==c


def test_required_deletion_and_budget_growth_rejected():
    c,a=fixture(); c[0]['requirement']='required'; a[0].update(kind='delete',outputs=[])
    assert not evaluate(c,a)['valid']


def test_elective_pool_minimum_cannot_be_replaced_by_required_course():
    c,a=fixture()
    delete=dict(a[0],kind='delete',outputs=[])
    new=deepcopy(a[0]); new.update(id='A2',kind='add',source_course_ids=[])
    new['outputs'][0].update(course_id='P:new',category='公共基础必修课',requirement='required')
    r=evaluate_actions(c,[delete,new],literature_ids=['L15'],skill_ids=['python','sql'],
        totals=[{'label':'专业选修课','credits':2,'hours':32}])
    assert not r['valid'] and any('选修池' in e for e in r['errors'])


def test_selected_elective_cannot_disappear_silently():
    c,a=fixture(); a[0]['outputs'][0]['course_id']='P:replacement'
    r=evaluate_actions(c,a,literature_ids=['L15'],skill_ids=['python','sql'],selected_electives=['P:c'])
    assert not r['valid'] and any('选修' in e for e in r['errors'])


def test_explicit_replacement_path_preserves_minimum():
    c,a=fixture(); a[0]['outputs'][0]['course_id']='P:replacement'
    r=evaluate_actions(c,a,literature_ids=['L15'],skill_ids=['python','sql'],selected_electives=['P:c'],
        selected_electives_after=['P:replacement'],totals=[{'label':'专业选修课','credits':2,'hours':32}])
    assert r['valid'] and r['proposed_path_check']['elective_minima_satisfied']
    c,a=fixture(); a[0]['outputs'][0]['credits']=3
    assert not evaluate(c,a)['valid']


def test_deferred_acceptance_displacement_stability_and_ties():
    ds=[{'id':'A','capacity':1,'minimum_score':60},{'id':'B','capacity':1,'minimum_score':60}]
    ss=[{'id':'low','preferences':['A','B'],'scores':{'A':70,'B':80},'eligible_directions':['A','B']},
        {'id':'high','preferences':['A','B'],'scores':{'A':90,'B':70},'eligible_directions':['A','B']},
        {'id':'fail','preferences':['A'],'scores':{'A':50},'eligible_directions':['A']}]
    r=allocate_directions(ss,ds)
    assert r['assignments']=={'high':'A','low':'B'} and r['stable']
    assert r['unmatched'][0]['student_id']=='fail'
    assert r==allocate_directions(list(reversed(ss)),ds) or r['assignments']==allocate_directions(list(reversed(ss)),ds)['assignments']
    ss[1]['scores']['A']=70
    assert allocate_directions(ss,ds,seed=11)['assignments']==allocate_directions(ss,ds,seed=11)['assignments']


def test_capacity_unknown_not_zero_and_bad_preferences():
    with pytest.raises(ValueError): allocate_directions([],[{'id':'A','capacity':None,'minimum_score':60}])
    with pytest.raises(ValueError): allocate_directions([{'id':'s','preferences':['missing'],'scores':{}}],[{'id':'A','capacity':1,'minimum_score':60}])
