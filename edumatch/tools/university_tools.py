"""Reusable university-centred plugin entry point."""
def specs():
    from .registry import ToolSpec
    from agent.university_workflow import run_university
    return [ToolSpec('university_analyze','university',
        '输入高校专业和目标职位任务包，分析四项任务、检查候选并生成网页。request.target_role 可设 software_engineer；role_course_mapping 连接职位词项、课程和动作。',
        {'type':'object','properties':{'brief':{'type':'object'},'output_directory':{'type':'string'}},
         'required':['brief','output_directory'],'additionalProperties':False},
        lambda _ds,args:run_university(args['brief'],args['output_directory']),requires_dataset=False)]
