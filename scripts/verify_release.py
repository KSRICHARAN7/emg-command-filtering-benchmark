"""Verify public release files, frozen inputs and published aggregate arithmetic."""
from pathlib import Path
import hashlib,json
import numpy as np
R=Path(__file__).resolve().parents[1]
def verify():
 m=json.loads((R/'PUBLIC_MANIFEST.json').read_text())
 for name,h in m['files_sha256'].items():
  p=R/name
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('Release file changed or absent: '+name)
 freeze=json.loads((R/'docs/step4_protocol/FREEZE_RECORD_v1.0.json').read_text())
 for name,h in freeze['frozen_file_sha256'].items():
  if hashlib.sha256((R/name).read_bytes()).hexdigest()!=h:raise ValueError('Frozen file changed: '+name)
 for ds in ['db5','db2']:
  rows=json.loads((R/f'results/{ds}/method_summary.json').read_text());assert len(rows)==(14 if ds=='db5' else 19)
  assert all(r['participants_meeting_all_constraints']==0 for r in rows)
 paired=json.loads((R/'results/db5/paired_statistics.json').read_text())['primary'];assert np.isclose(np.mean(paired['participant_differences_pp']),paired['mean_difference_pp'])
 for c in json.loads((R/'results/db2/paired_contrasts.json').read_text()).values():assert np.isclose(np.mean(c['participant_differences_pp']),c['mean_difference_pp'])
 print(f'PASS: {len(m["files_sha256"])} release hashes, 9 frozen dependencies, aggregate arithmetic',flush=True)
 return True
if __name__=='__main__':verify()
