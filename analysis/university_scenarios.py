"""Action-linked capacity stress test; scenario capacities are assumptions, not school facts."""
from math import ceil,floor


def capacity_stress(base=30,teacher_hours=92,lab_per_student=68,review_minutes=20):
    """Find feasible one-cohort pilot sizes under three declared resource envelopes.

    Existing-cohort use must already have been deducted from the hypothetical envelope.
    This is a module-level feasibility test, never a full-major intake recommendation.
    """
    if base<=0 or teacher_hours<=0 or lab_per_student<=0 or review_minutes<0:
        raise ValueError('资源系数须合法')
    def required(n,initial_extra=0):
        return {'teacher_hours':ceil(n/30)*(teacher_hours+initial_extra)+n*review_minutes/60,
                'lab_seat_hours':n*(lab_per_student+initial_extra)}
    scenarios=[('悲观',100,1900),('基准',110,2100),('乐观',210,2500)]
    rows=[]
    for name,t,l in scenarios:
        sizes=[n for n in range(1,61) if required(n)['teacher_hours']<=t and required(n)['lab_seat_hours']<=l]
        feasible=max(sizes,default=0)
        before=required(base,8);after=required(base)
        pilot=min(base,feasible)
        req=required(pilot) if pilot else {'teacher_hours':0,'lab_seat_hours':0}
        rows.append({'scenario':name,'capacity_status':'project_assumption_not_verified',
            'assumed_available_teacher_hours':t,'assumed_available_lab_seat_hours':l,
            'fixed_30_initial_extra8':before,'fixed_30_final':after,
            'initial_teacher_shortfall':max(0,before['teacher_hours']-t),
            'final_teacher_shortfall':max(0,after['teacher_hours']-t),
            'initial_lab_shortfall':max(0,before['lab_seat_hours']-l),
            'final_lab_shortfall':max(0,after['lab_seat_hours']-l),
            'max_feasible_pilot_size_up_to60':feasible,'gated_pilot_size':pilot,
            'gated_teacher_required':req['teacher_hours'],'gated_lab_required':req['lab_seat_hours'],
            'gated_feasible':req['teacher_hours']<=t and req['lab_seat_hours']<=l})
    return {'scope':'单个新教学组的两门课试点；先扣除其他课程与已有年级占用的资源余量',
        'parameters':{'base_pilot_size':base,'class_size':30,'contact_hours':teacher_hours,
            'lab_hours_per_student':lab_per_student,'review_minutes_per_student':review_minutes},
        'rows':rows,'initial_vs_final_reduction_at30':{'teacher_hours':8,'lab_seat_hours':240},
        'reduction_reference':'被预算检查否决的加8学时初稿；不是相对原培养方案的真实资源节约',
        'baseline_actual_capacity':None,'learning_effect':None,
        'interpretation':'三情景仅量化资源可行性及回退机制；不能由条件包络认定本校容量或实际扩招人数。'}
