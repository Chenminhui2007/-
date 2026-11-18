import json
import pytest
from analysis.evidence_metrics import coverage, resource_pressure, compare_coverage
from agent.evidence_session import append_event, read_session, public_summary


def case():
    tasks=[dict(id=k, definition='Synthetic observable task', framework_reference='synthetic fixture', mapping_reviewed=True) for k in ('a','b')]
    return dict(tasks=tasks, postings=[dict(id='1',task_ids=['a','a','b']),dict(id='2',task_ids=['a'])], evidence=[], curriculum_version='v',path_verified=True)


def evidence(k, status):
    return dict(task_id=k,status=status,curriculum_version='v',source_id='test',locator='p1',reviewer='test',scope='current_teaching',outcome='o',activity='a',assessment='e',task_level_review=True,full_path_reviewed=True,absence_reason='reviewed')


def test_unknown_not_zero_and_duplicate_label():
    r=coverage(**case())
    assert r['lower']==0 and r['upper']==100 and r['point'] is None
    assert r['rows'][0]['count']==2 and r['rows'][0]['weight']==pytest.approx(2/3)


def test_confirmed_and_absent():
    c=case(); c['evidence']=[evidence('a','C'),evidence('b','A')]
    r=coverage(**c)
    assert r['point']==pytest.approx(200/3) and r['total_score'] is None


def test_proposal_and_conflict_remain_unknown():
    c=case(); proposed=evidence('b','C'); proposed['scope']='proposed'
    c['evidence']=[evidence('a','C'),evidence('a','A'),proposed]
    r=coverage(**c)
    assert r['conflicts']==['a'] and r['unknown_weight']==100


@pytest.mark.parametrize('field', ['path_verified','mapping'])
def test_unverified_gate(field):
    c=case()
    if field=='mapping': c['tasks'][0]['mapping_reviewed']=False
    else: c[field]=False
    assert coverage(**c)['lower'] is None


def test_duplicate_ads_rejected():
    c=case(); c['postings'].append(c['postings'][0])
    with pytest.raises(ValueError): coverage(**c)


def test_resource_unknown_zero_and_assumption():
    rows=[dict(id=str(i),unit='hours',period='2027',demand=10,available=a) for i,a in enumerate([None,0,20])]
    r=resource_pressure(rows)
    assert r[0]['overload'] is None and r[1]['shortfall']==10 and r[2]['status']=='conditional'


def test_comparison_requires_confirmation():
    meta={'measurement_hash':'fixture','evidence_snapshot':'fixture'}
    b={'lower':20,'upper':40,**meta}; a={'lower':30,'upper':60,**meta}
    assert compare_coverage(b,a)['delta'] is None
    assert compare_coverage(b,a,same_measurement=True)['delta']=={'lower':-10,'upper':40}


def test_session_privacy_revision_and_tamper(tmp_path):
    p=tmp_path/'session.jsonl'
    append_event(p,kind='input',origin='student_self_report',payload={'text':'PRIVATE STUDENT'})
    proposal=append_event(p,kind='proposal',origin='agent_proposal',payload={'action':'test'})
    with pytest.raises(ValueError): append_event(p,kind='revision',origin='agent_proposal',payload={})
    append_event(p,kind='revision',origin='agent_proposal',payload={},parent=proposal['hash'],reason='constraint failed')
    assert len(read_session(p))==3
    assert 'PRIVATE' not in json.dumps(public_summary(p))
    p.write_text(p.read_text(encoding='utf-8').replace('PRIVATE','ALTERED'),encoding='utf-8')
    with pytest.raises(ValueError): read_session(p)


def test_student_not_institution(tmp_path):
    with pytest.raises(ValueError): append_event(tmp_path/'s',kind='diagnosis',origin='student_self_report',payload={})
    with pytest.raises(ValueError): append_event(tmp_path/'s',kind='input',origin='institution_statement',payload={})


def test_registered_tools_do_not_build_dataset():
    from edumatch.tools.registry import call_tool, list_tools
    assert len(list_tools('evidence_v2'))==5
    assert call_tool('evidence_v2_coverage', case())['point'] is None


def test_changed_measurement_rejects_comparison():
    c=case(); c['evidence_snapshot']='frozen'
    before=coverage(**c)
    c['postings'][0]['task_ids']=['b']
    after=coverage(**c)
    assert compare_coverage(before,after,same_measurement=True)['delta'] is None


def test_string_review_flag_not_boolean():
    c=case(); e=evidence('a','C'); e['task_level_review']='false'; c['evidence']=[e]
    assert coverage(**c)['rows'][0]['state']=='U'


def test_evaluation_unknown_capacity_and_revision(tmp_path):
    from agent.evidence_session import evaluate_and_record
    c={'course_id':'P:c','program_id':'P','course_name':'Synthetic','category':'专业选修课','requirement':'elective_pool','credits':2,'hours_total':32,'eligible_for_computation':True}
    output=dict(c,learning_outcome='Synthetic observable task',assessment='Independent task',activities=[{'description':'Practice','hours':32,'skill_ids':['t']}],prerequisites=[],teaching_year=3)
    action=dict(id='A',kind='revise',source_course_ids=['P:c'],outputs=[output],rationale='Synthetic test only',literature_ids=['L'],demand_skill_ids=['t'],effective_entry_year=2027)
    args=dict(courses=[c],actions=[action],literature_ids=['L'],task_ids=['t'])
    p=tmp_path/'case.jsonl'
    first=evaluate_and_record(args,p)
    assert first['status']=='conditional' and not first['implemented']
    args['resources']=[dict(id='lab',demand=32,available=16,unit='seat hours',period='2027')]
    second=evaluate_and_record(args,p,first['proposal_event_hash'],'Added resource assumption reveals overload')
    assert second['status']=='infeasible_under_inputs' and not second['accepted_for_comparison']
    assert [e['kind'] for e in read_session(p)]==['proposal','evaluation','revision','evaluation']
