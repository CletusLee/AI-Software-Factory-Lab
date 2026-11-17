"""Load and validate the versioned, file-based factory definition registry."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def definition_root():
    configured = os.getenv('FACTORY_DEFINITIONS')
    if configured:
        return Path(configured)
    marker = ROOT / 'deployment' / 'active.txt'
    if marker.exists():
        revision = marker.read_text(encoding='utf-8').strip()
        candidate = ROOT / 'deployment' / 'releases' / revision / 'definitions'
        if candidate.is_dir():
            return candidate
        raise ValueError(f'Active release is missing: {revision}')
    mounted = ROOT / 'definitions'
    default = mounted if mounted.is_dir() else ROOT.parents[1] / 'definitions'
    return Path(os.getenv('FACTORY_SHARED_DEFINITIONS', str(default)))


def revision(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*'), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b'\0')
            digest.update(path.read_bytes())
            digest.update(b'\0')
    return digest.hexdigest()[:16]


def load(root=None):
    root = Path(root) if root else definition_root()
    result = {}
    for plural, filename in [('agents', 'agent.json'), ('teams', 'team.json'), ('workflows', 'workflow.json')]:
        items = {}
        for path in sorted((root / plural).glob('*/' + filename)):
            obj = json.loads(path.read_text(encoding='utf-8'))
            if obj['id'] in items or (plural != 'agents' and obj['id'] != path.parent.name):
                raise ValueError(f'Duplicate or mismatched ID: {path}')
            if plural in ('agents', 'teams'):
                obj['prompt'] = (path.parent / 'prompt.md').read_text(encoding='utf-8').strip()
                if not obj['prompt']:
                    raise ValueError(f'Empty prompt: {path}')
            items[obj['id']] = obj
        if not items:
            raise ValueError(f'No {plural} found under {root}')
        result[plural] = items
    skills = {}
    for path in sorted((root / 'skills').glob('*/SKILL.md')):
        text = path.read_text(encoding='utf-8')
        if not text.startswith('---\n') or f'name: {path.parent.name}\n' not in text:
            raise ValueError(f'Invalid skill header: {path}')
        skills[path.parent.name] = path
    result['skills'] = skills
    for agent in result['agents'].values():
        missing = set(agent.get('skills', [])) - skills.keys()
        if missing:
            raise ValueError(f"{agent['id']}: unknown skills {sorted(missing)}")
    for team in result['teams'].values():
        missing = set(team['members']) - result['agents'].keys()
        if missing or not team['members']:
            raise ValueError(f"{team['id']}: invalid members {sorted(missing)}")
    for flow in result['workflows'].values():
        seen = set()
        def validate(steps):
            for step in steps:
                name = step['name']
                if name in seen:
                    raise ValueError(f"{flow['id']}: duplicate step {name}")
                seen.add(name)
                kind = step['type']
                if kind == 'agent' and step['ref'] not in result['agents']:
                    raise ValueError(f'{name}: unknown agent')
                if kind == 'team' and step['ref'] not in result['teams']:
                    raise ValueError(f'{name}: unknown team')
                if kind not in ('agent', 'team', 'executor', 'condition', 'parallel'):
                    raise ValueError(f'{name}: unknown type {kind}')
                if kind in ('condition', 'parallel'):
                    validate(step['steps'])
                if kind == 'condition':
                    validate(step['else_steps'])
        validate(flow['steps'])
    result['root'] = root
    result['revision'] = revision(root)
    return result
