"""Reproducible CLI and MCP smoke checks using synthetic examples only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as folder:
        out=Path(folder)
        def command(*args):
            subprocess.run([sys.executable,'scripts/evidence_agent.py',*map(str,args)],cwd=ROOT,check=True,capture_output=True)
        command('coverage','--input','examples/evidence_v2/coverage.json','--output',out/'coverage.json')
        coverage=json.loads((out/'coverage.json').read_text(encoding='utf-8'))
        assert coverage['point'] is None and coverage['lower']==0 and coverage['upper']==100
        command('evaluate','--input','examples/evidence_v2/proposal.json','--session',out/'events.jsonl','--output',out/'proposal.json')
        proposal=json.loads((out/'proposal.json').read_text(encoding='utf-8'))
        assert proposal['status']=='conditional' and not proposal['implemented']
        command('public-summary','--session',out/'events.jsonl','--output',out/'summary.json')
        summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
        assert summary['event_count']==2 and all('payload' not in r for r in summary['events'])
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize'},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'evidence_v2_coverage',
                'arguments':json.loads((ROOT/'examples/evidence_v2/coverage.json').read_text(encoding='utf-8'))}}]
        run=subprocess.run([sys.executable,'-m','mcp_servers.server','--group','evidence_v2'],cwd=ROOT,
            input=''.join(json.dumps(r)+'\n' for r in requests),text=True,encoding='utf-8',capture_output=True,check=True)
        replies=[json.loads(line) for line in run.stdout.splitlines() if line.strip()]
        assert len(replies)==3 and len(replies[1]['result']['tools'])==5
        result=json.loads(replies[2]['result']['content'][0]['text'])
        assert result['point'] is None and result['upper']==100
    print(json.dumps({'status':'passed','checks':['CLI coverage','CLI proposal','private ledger','safe public summary','MCP initialize','MCP list 5 tools','MCP coverage call'],'data':'synthetic only'}))


if __name__=='__main__':
    main()
