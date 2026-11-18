"""Reusable university-centred plugin entry point."""
def specs():
    from .registry import ToolSpec
    from agent.university_workflow import run_university
    return [ToolSpec('university_analyze','university',
        '输入高校专业任务包，依次分析四任务、检查候选、保留过程JSON与日志并生成本地网页；已有目录拒绝覆盖。候选由调用AI提供。',
        {'type':'object','properties':{'brief':{'type':'object'},'output_directory':{'type':'string'}},
         'required':['brief','output_directory'],'additionalProperties':False},
        lambda _ds,args:run_university(args['brief'],args['output_directory']),requires_dataset=False)]
