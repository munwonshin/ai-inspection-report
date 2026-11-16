"""Create a new synthetic-only root for the real bundled EXE diagnostic."""
import argparse,json,os
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO))
from qa.c1_baseline.run_baseline import configure_dependencies,create_pdf
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--deps-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();dll=configure_dependencies(args.deps_dir)
root=args.output.resolve()
if str(root).startswith('\\\\'):raise SystemExit('Local test folder required')
root.mkdir(parents=True,exist_ok=False)
for name in ('inputs','outputs','evidence','runtime-temp'):(root/name).mkdir()
fixture=json.loads((REPO/'qa/c1_baseline/fixtures.json').read_text(encoding='utf-8'))
(root/'inputs/fixture.json').write_text(json.dumps(fixture,ensure_ascii=False,indent=2),encoding='utf-8')
for profile in ('A','B'):(root/'inputs'/('plan_'+profile+'.pdf')).write_bytes(create_pdf(fixture['profiles'][profile]))
print('SYNTHETIC_FROZEN_ROOT_READY',root)
