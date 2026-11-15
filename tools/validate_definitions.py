"""Validate cross-POC definition IDs and references using the standard library."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'definitions'


def read_items(kind, filename):
    items = {}
    for path in (ROOT / kind).glob('*/' + filename):
        item = json.loads(path.read_text(encoding='utf-8'))
        identifier = item['id']
        if identifier in items:
            raise ValueError(f'Duplicate {kind} ID: {identifier}')
        if kind in ('agents', 'teams') and not (path.parent / 'prompt.md').read_text(encoding='utf-8').strip():
            raise ValueError(f'Empty prompt: {identifier}')
        items[identifier] = item
    if not items:
        raise ValueError(f'No {kind} definitions')
    return items


def validate():
    agents = read_items('agents', 'agent.json')
    teams = read_items('teams', 'team.json')
    workflows = read_items('workflows', 'workflow.json')
    skills = {path.parent.name for path in (ROOT / 'skills').glob('*/SKILL.md')}
    for agent in agents.values():
        missing = set(agent.get('skills', [])) - skills
        if missing:
            raise ValueError(f"{agent['id']}: missing skills {sorted(missing)}")
    for team in teams.values():
        missing = set(team['members']) - agents.keys()
        if missing or not team['members']:
            raise ValueError(f"{team['id']}: invalid members {sorted(missing)}")
    def steps(items, seen):
        for step in items:
            if step['name'] in seen:
                raise ValueError(f"Duplicate workflow step: {step['name']}")
            seen.add(step['name'])
            kind = step['type']
            if kind in ('agent', 'team') and step['ref'] not in (agents if kind == 'agent' else teams):
                raise ValueError(f"{step['name']}: unknown {kind} {step['ref']}")
            if kind not in ('agent', 'team', 'executor', 'condition', 'parallel'):
                raise ValueError(f"{step['name']}: unknown type {kind}")
            if kind in ('condition', 'parallel'):
                steps(step['steps'], seen)
            if kind == 'condition':
                steps(step['else_steps'], seen)
    for workflow in workflows.values():
        steps(workflow['steps'], set())
    references = json.loads((ROOT / 'reference_relationships.json').read_text(encoding='utf-8'))
    for relation in references['relationships']:
        if relation['source'] not in agents or relation['target'] not in agents:
            raise ValueError(f'Unknown agent in reference relationship: {relation}')
    print(f'Valid: {len(agents)} agents, {len(teams)} teams, {len(skills)} skills, {len(workflows)} workflows')


if __name__ == '__main__':
    validate()
