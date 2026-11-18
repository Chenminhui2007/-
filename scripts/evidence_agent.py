"""Portable JSON CLI for the conversation-orchestrated evidence workflow."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.evidence_session import append_event, public_summary, run_diagnosis, evaluate_and_record
from analysis.evidence_metrics import coverage, resource_pressure, compare_coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['diagnose', 'coverage', 'resources', 'compare', 'evaluate', 'record', 'public-summary'])
    parser.add_argument('--input', type=Path)
    parser.add_argument('--session', type=Path)
    parser.add_argument('--data-root', type=Path, help='Competition data directory; default is local private data')
    parser.add_argument('--parent', help='Previous proposal event hash for a revision')
    parser.add_argument('--reason', help='Evidence-based reason for revision')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8-sig')) if args.input else {}
    if args.command == 'diagnose':
        from edumatch.competition_data import CompetitionData
        result = run_diagnosis(data, args.session, CompetitionData.load(args.data_root))
    elif args.command == 'coverage':
        result = coverage(**data)
    elif args.command == 'resources':
        result = resource_pressure(data['rows'])
    elif args.command == 'compare':
        result = compare_coverage(**data)
    elif args.command == 'evaluate':
        result = evaluate_and_record(data, args.session, args.parent, args.reason)
    else:
        if not args.session:
            parser.error('--session is required')
        result = append_event(args.session, **data) if args.command == 'record' else public_summary(args.session)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


if __name__ == '__main__':
    main()
