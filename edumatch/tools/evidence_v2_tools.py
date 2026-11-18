"""Evidence v2 tools; no legacy dataset is constructed for pure calculations."""
def specs():
    from .registry import ToolSpec
    from analysis.evidence_metrics import coverage, resource_pressure, compare_coverage
    from agent.evidence_session import run_diagnosis
    from analysis.evidence_proposals import evaluate_proposal
    definitions = [
        ('evidence_v2_diagnose', '信管三维诊断与证据门槛；无综合总分', lambda a: run_diagnosis(a.get('request', {})), {'request': {'type':'object'}}, []),
        ('evidence_v2_coverage', '任务级C/A/U教学证据覆盖；不完整路径禁止正式分数', lambda a: coverage(**a),
         {'tasks':{'type':'array','items':{'type':'object'}}, 'postings':{'type':'array','items':{'type':'object'}},
          'evidence':{'type':'array','items':{'type':'object'}},'curriculum_version':{'type':'string'},'path_verified':{'type':'boolean'},'evidence_snapshot':{'type':'string'}},
         ['tasks','postings','evidence','curriculum_version']),
        ('evidence_v2_resources', '同单位同期间资源压力；真实证据与条件假设分列', lambda a: resource_pressure(a['rows']),
         {'rows':{'type':'array','items':{'type':'object'}}}, ['rows']),
        ('evidence_v2_compare', '同口径覆盖识别区间差；不是因果效果', lambda a: compare_coverage(**a),
         {'before':{'type':'object'},'after':{'type':'object'},'same_measurement':{'type':'boolean'}}, ['before','after']),
        ('evidence_v2_evaluate', '课程约束、文献支持定位、资源条件和动作风险分列；不生成虚假总分',lambda a:evaluate_proposal(**a),
         {'courses':{'type':'array','items':{'type':'object'}},'actions':{'type':'array','items':{'type':'object'}},
          'literature_ids':{'type':'array','items':{'type':'string'}},'task_ids':{'type':'array','items':{'type':'string'}},
          'resources':{'type':'array','items':{'type':'object'}},'budget':{'type':'object'},'totals':{'type':'array','items':{'type':'object'}},
          'selected_electives':{'type':'array','items':{'type':'string'}},'selected_electives_after':{'type':'array','items':{'type':'string'}}},
         ['courses','actions','literature_ids','task_ids'])]
    return [ToolSpec(name, 'evidence_v2', description,
        {'type':'object','properties':properties,'required':required,'additionalProperties':False},
        lambda _ds, args, fn=fn: fn(args), requires_dataset=False)
        for name,description,fn,properties,required in definitions]
