import hashlib,json
from pathlib import Path
import pytest
from analysis.university_scenarios import capacity_stress
from agent.university_workflow import run_university
from agent.evidence_session import read_session


def test_capacity_steps_and_hypothesis_scope():
    r=capacity_stress();assert r['baseline_actual_capacity'] is None
    assert [x['gated_pilot_size'] for x in r['rows']]==[24,30,30]
    assert all(x['gated_feasible'] for x in r['rows'])
    assert r['initial_vs_final_reduction_at30']=={'teacher_hours':8,'lab_seat_hours':240}
    assert r['rows'][1]['max_feasible_pilot_size_up_to60']==30


def test_real_case_complete_artifacts_and_rejection(tmp_path):
    root=Path(__file__).resolve().parents[1]
    if not (root/'data/university_cases/BJUT_IM_2024.json').exists():
        pytest.skip('真实高校数据仅本地保存；公开包不包含此集成输入')
    brief=json.loads((root/'data/university_cases/BJUT_IM_2024.json').read_text(encoding='utf-8'))
    run_university(brief,tmp_path)
    proposal=json.loads((tmp_path/'results/02_proposal.json').read_text(encoding='utf-8'))
    assert proposal['candidates'][0]['evaluation']['status']=='infeasible_under_inputs'
    assert proposal['candidates'][1]['evaluation']['status']=='conditional'
    assert proposal['candidates'][1]['evaluation']['curriculum_constraints']['delta']['hours_total']==0
    events=read_session(tmp_path/'process/events.jsonl')
    assert any(x['kind']=='revision' for x in events)
    assert all(x['origin']!='student_self_report' for x in events)
    manifest=json.loads((tmp_path/'run_manifest.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((tmp_path/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in manifest['files'])
    page=(tmp_path/'index.html').read_text(encoding='utf-8')
    assert '任务1' in page and '任务4' in page and '102' in page
    if brief['request'].get('target_role')=='software_engineer':
        inputs=json.loads((tmp_path/'inputs/university_input.json').read_text(encoding='utf-8'))
        result=json.loads((tmp_path/'results/01_diagnosis.json').read_text(encoding='utf-8'))
        alignment=result['diagnosis']['role_alignment']
        assert inputs['courses'] and inputs['published_plans'] and inputs['sources']
        assert alignment['posting_count']==result['diagnosis']['skills']['demand']['n_postings']>0
        assert alignment['rows'] and all(row['courses'] for row in alignment['rows'])
        assert '信管培养方案与软件工程师对照' in page and 'inputs/university_input.json' in page
    with pytest.raises(ValueError,match='已有内容'): run_university(brief,tmp_path)


def test_university_tool_available_without_loading_data():
    from mcp_servers.server import MCPServer
    server=MCPServer('university')
    assert [t['name'] for t in server.tools]==['university_analyze']
    assert server._dataset_cache is None
