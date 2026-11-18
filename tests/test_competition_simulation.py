import pytest
from analysis.competition_simulation import simulate_pair,scenario_suite,DEFAULT_PARAMETERS,update_intake


def test_four_year_lag_shared_baseline_and_missing_stock():
    r=simulate_pair(82,{'name':'积极','demand_index':1.2,'employment_signal':.96})
    rows=r['rows']
    assert all(x['adjusted']['modelled_graduates'] is None for x in rows[:3])
    assert rows[3]['adjusted']['modelled_graduates']==82
    assert all(x['employment_feedback_assumption'] is None for x in rows[:4])
    assert all(x['adjusted']['total_in_school'] is None and x['recommended_intake'] is None for x in rows)
    assert all(x['baseline']['conditional_intake']==82 for x in rows)
    assert all(x['adjusted']['verified_capacity_sufficient'] is None for x in rows)


def test_fixed_signal_converges_without_overshoot():
    for demand,signal in ((.8,.8),(1,.9),(1.2,.96)):
        current=82; streak=0; values=[]
        for _ in range(60):
            old=current; current,streak,target=update_intake(current,82,demand,signal,streak,DEFAULT_PARAMETERS)
            assert abs(current-old)<=max(1,int(old*.05))
            values.append(current)
        assert current==target and len(set(values[-10:]))==1
        assert all(x<=target for x in values) if demand>1 else all(x>=target for x in values)


def test_missing_or_incompatible_feedback_does_not_expand():
    for signal in (None,.8,.9):
        r=simulate_pair(30,{'name':'条件','demand_index':1.2,'employment_signal':signal})
        assert all(x['adjusted']['conditional_intake']==30 for x in r['rows'])


def test_shock_bounds_deadband_and_persistence():
    sc={'name':'冲击','demand_path':[1.2]*5+[.5]*7,'employment_path':[.96]*5+[.7]*7}
    r=simulate_pair(30,sc,{'years':12})
    assert all(21<=x['adjusted']['conditional_intake']<=39 for x in r['rows'])
    assert r['rows'][4]['adjusted']['conditional_intake']==30  # one positive feedback is insufficient
    assert r['rows'][5]['adjusted']['conditional_intake']==30  # direction reversal resets streak


def test_parameters_sensitivity_and_invalid_inputs():
    s=scenario_suite(30)
    assert len(s['runs'])==3 and len(s['sensitivity'])==27 and all(x['fixed_last_10'] for x in s['fixed_signal_checks'])
    for p in ({'years':3},{'retention':1.1},{'available_teacher_hours':-1},{'max_step_fraction':0},{'module_contact_hours':None}):
        with pytest.raises(ValueError): scenario_suite(30,p)
