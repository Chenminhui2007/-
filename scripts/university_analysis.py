"""Run a university input package and retain result web page and process evidence."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.university_workflow import run_university
from edumatch.competition_data import CompetitionData

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data-root',type=Path)
    args=parser.parse_args()
    brief=json.loads(args.input.read_text(encoding='utf-8-sig'))
    print(json.dumps(run_university(brief,args.output,CompetitionData.load(args.data_root)),ensure_ascii=True))
