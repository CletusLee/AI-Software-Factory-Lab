"""Validate, snapshot and deploy factory definitions using Python and Compose."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from integration.registry import load, revision
from integration.export_catalog import export

ROOT = Path(__file__).resolve().parent.parent
SHARED_DEFINITIONS = ROOT.parents[1] / 'definitions'
DEPLOY = ROOT / 'deployment'
RELEASES = DEPLOY / 'releases'
ACTIVE = DEPLOY / 'active.txt'
LAST = DEPLOY / 'last-good.txt'
LOCK = DEPLOY / '.deploy.lock'


def read(path):
    return path.read_text(encoding='utf-8').strip() if path.exists() else ''


def mark(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(value + '\n', encoding='utf-8')
    temporary.replace(path)


def verify(reg):
    names = [a['name'] for a in reg['agents'].values()]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate agent names')
    handlers = {'evidence_gate','is_ready','candidate_passed','apply_candidate_change','verify_candidate',
                'blocked_result','pending_approval','require_observability','require_governance'}
    def check(steps):
        for s in steps:
            if s['type'] in ('executor','condition') and s.get('ref') not in handlers:
                raise ValueError(f"Unknown handler: {s.get('ref')}")
            if s['type'] in ('condition', 'parallel'): check(s['steps'])
            if s['type'] == 'condition': check(s['else_steps'])
    for f in reg['workflows'].values(): check(f['steps'])
    print(f"Valid revision {reg['revision']}: {len(reg['agents'])} agents, {len(reg['teams'])} teams, {len(reg['skills'])} skills, {len(reg['workflows'])} workflows")


def compose(*args):
    subprocess.run(['docker','compose',*args], cwd=ROOT, check=True)


def local_key():
    if os.getenv('OS_SECURITY_KEY'): return os.environ['OS_SECURITY_KEY']
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('OS_SECURITY_KEY='):
                return line.split('=',1)[1].strip().strip('"\'')
    return ''


def request(url, key=''):
    headers = {'Authorization': 'Bearer ' + key} if key else {}
    with urlopen(Request(url, headers=headers), timeout=5) as response:
        return json.load(response)


def health(reg):
    expected = reg['revision']
    deadline = time.monotonic() + 120
    error = None
    while time.monotonic() < deadline:
        try:
            # Use the internal network: Docker Desktop may not expose a host port
            # to the shell that launches the pipeline.
            probe = ("import json,os,urllib.request; "
                     "r=urllib.request.Request('http://127.0.0.1:7777/factory/revision',"
                     "headers={'Authorization':'Bearer '+os.environ['OS_SECURITY_KEY']}); "
                     "print(urllib.request.urlopen(r,timeout=5).read().decode())")
            output = subprocess.check_output(['docker','compose','exec','-T','agentos','python','-c',probe],
                                             cwd=ROOT, text=True, stderr=subprocess.DEVNULL, timeout=10)
            api = json.loads(output)
            guest = request('http://127.0.0.1:7007/api/auth/guest/refresh')['backstageIdentity']['token']
            catalog = request('http://127.0.0.1:7007/api/catalog/entities/by-name/component/default/factory-04', guest)
            if api['revision'] != expected or catalog['metadata']['annotations'].get('factory.local/revision') != expected:
                raise ValueError('Services have not converged on the selected revision')
            model = request('http://127.0.0.1:7778/v1/models')
            ids = {x['id'] for x in model['data']}
            if ids != set(reg['agents']) | set(reg['teams']):
                raise ValueError('Gateway target IDs do not match the registry')
            print(f'AgentOS, Gateway and Backstage match revision {expected}')
            return
        except (OSError, URLError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            error = exc
            time.sleep(3)
    raise RuntimeError(f'Service verification timed out: {error}')


def activate(rev, previous):
    if not re.fullmatch(r'[0-9a-f]{16}', rev):
        raise ValueError('Invalid revision identifier')
    reg = load(RELEASES / rev / 'definitions')
    verify(reg)
    if reg['revision'] != rev:
        raise ValueError('Release content does not match its revision')
    export(reg)
    mark(ACTIVE, rev)
    try:
        compose('up','-d','--no-deps','--force-recreate','agentos','agno-gateway','librechat','backstage')
        health(reg)
    except Exception:
        if previous and (RELEASES / previous / 'definitions').is_dir() and previous != rev:
            print(f'Deployment failed; restoring {previous}', file=sys.stderr)
            export(load(RELEASES / previous / 'definitions'))
            mark(ACTIVE, previous)
            try:
                compose('up','-d','--no-deps','--force-recreate','agentos','agno-gateway','librechat','backstage')
            except Exception as exc:
                print(f'Automatic service restoration also failed: {exc}', file=sys.stderr)
        elif not previous:
            ACTIVE.unlink(missing_ok=True)
            export(load(SHARED_DEFINITIONS))
            try:
                compose('up','-d','--no-deps','--force-recreate','agentos','agno-gateway','librechat','backstage')
            except Exception as exc:
                print(f'Automatic source restoration also failed: {exc}', file=sys.stderr)
        raise
    if previous and previous != rev:
        mark(LAST, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate')
    sub.add_parser('deploy')
    sub.add_parser('status')
    rollback = sub.add_parser('rollback')
    rollback.add_argument('--revision', help='release hash; defaults to last successful revision')
    args = parser.parse_args()
    RELEASES.mkdir(parents=True, exist_ok=True)
    if args.command == 'validate':
        verify(load(SHARED_DEFINITIONS))
        return
    if args.command == 'status':
        print(f"Active: {read(ACTIVE) or '(source definitions)'}; previous: {read(LAST) or '(none)'}")
        print('Releases:', ', '.join(p.name for p in sorted(RELEASES.iterdir()) if p.is_dir()) or '(none)')
        return
    try:
        LOCK.mkdir()
    except FileExistsError:
        raise RuntimeError('Another deployment is running (deployment/.deploy.lock exists)')
    try:
        previous = read(ACTIVE)
        if args.command == 'rollback':
            target = args.revision or read(LAST)
            if not target: raise ValueError('No previous release available')
        else:
            source = SHARED_DEFINITIONS
            reg = load(source)
            verify(reg)
            target = reg['revision']
            destination = RELEASES / target / 'definitions'
            if not destination.exists():
                shutil.copytree(source, destination)
            if revision(destination) != target:
                raise ValueError('Snapshot checksum mismatch')
        activate(target, previous)
    finally:
        LOCK.rmdir()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Deployment error: {exc}', file=sys.stderr)
        sys.exit(1)
