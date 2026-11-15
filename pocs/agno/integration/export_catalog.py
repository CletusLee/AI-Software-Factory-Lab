"""Render Backstage and LibreChat configuration from the deployed registry."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from integration.registry import load


def workflow_edges(flow):
    """Project consecutive executable targets; executor/condition nodes remain control flow.

    Edges are *possible static control-flow handoffs*, not observed invocations.
    """
    edges = set()
    def walk(steps, incoming):
        current = set(incoming)
        for s in steps:
            if s['type'] in ('agent', 'team'):
                target = s['ref']
                edges.update((source, target) for source in current if source != target)
                current = {target}
            elif s['type'] == 'parallel':
                current = set().union(*(walk([branch], current) for branch in s['steps']))
            elif s['type'] == 'condition':
                current = walk(s['steps'], current) | walk(s['else_steps'], current)
        return current
    walk(flow['steps'], set())
    return edges


def render(registry):
    agents, teams, flows, skills = (registry[k] for k in ('agents', 'teams', 'workflows', 'skills'))
    rev = registry['revision']
    references_path = registry['root'] / 'reference_relationships.json'
    references = json.loads(references_path.read_text(encoding='utf-8'))['relationships'] if references_path.exists() else []
    edges = {key: workflow_edges(flow) for key, flow in flows.items()}
    entities = [
        {'apiVersion':'backstage.io/v1alpha1', 'kind':'Group', 'metadata':{'name':'factory-maintainers'}, 'spec':{'type':'team','children':[]}},
        {'apiVersion':'backstage.io/v1alpha1', 'kind':'System', 'metadata':{'name':'ai-factory'}, 'spec':{'owner':'factory-maintainers'}}]
    def component(key, title, kind, description, deps=()):
        entities.append({'apiVersion':'backstage.io/v1alpha1','kind':'Component',
            'metadata':{'name':key,'title':title,'description':description,'tags':[kind],
                        'annotations':{'factory.local/revision':rev}},
            'spec':{'type':kind,'lifecycle':'experimental','owner':'factory-maintainers',
                    'system':'ai-factory','dependsOn':[f'component:default/{d}' for d in sorted(set(deps))]}})
    def labels(key):
        pairs = [(fid, s, t) for fid, relations in edges.items() for s, t in relations if key in (s,t)]
        names = {**{x: v['name'] for x,v in agents.items()}, **{x:v['name'] for x,v in teams.items()}}
        upstream = [f'{names[s]} ({fid})' for fid,s,t in pairs if t == key]
        downstream = [f'{names[t]} ({fid})' for fid,s,t in pairs if s == key]
        planned = [r['description'] for r in references if key in (r['source'], r['target'])]
        return ('\n可能前序：' + (', '.join(upstream) or '無') + '\n可能後續：' + (', '.join(downstream) or '無')
                + '\n參考架構的設計關係（需各 POC 實作與驗證）：' + ('；'.join(planned) or '無'))
    for spec in agents.values():
        key = spec['id']
        upstream = [s for relations in edges.values() for s,t in relations if t == key]
        membership = [team['name'] for team in teams.values() if key in team['members']]
        desc = (f"{spec['summary']}\n輸入：{spec['inputs']}\n輸出：{spec['outputs']}\n"
                f"Team：{', '.join(membership) or '無'}\nSkills：{', '.join(spec['skills'])}\n"
                f"版本：{rev}\n{labels(key)}\n\nPrompt：\n{spec['prompt']}\n\n"
                '關係為流程定義中的可能交接，非 Langfuse 實際執行紀錄。')
        component(key, spec['name'], 'agent', desc, upstream + ['skill-' + s for s in spec['skills']])
    for spec in teams.values():
        key = spec['id']
        upstream = [s for relations in edges.values() for s,t in relations if t == key]
        names = ', '.join(agents[m]['name'] for m in spec['members'])
        component(key, spec['name'], 'agent-team', f"成員：{names}\n{labels(key)}\n\n{spec['prompt']}\n成員為可委派對象，實際委派請查閱執行 Trace。", spec['members'] + upstream)
    for key, path in skills.items():
        component('skill-' + key, key, 'agent-skill', path.read_text(encoding='utf-8'))
    def references(steps):
        found = []
        for s in steps:
            if s['type'] in ('agent', 'team'): found.append(s['ref'])
            if s['type'] in ('parallel', 'condition'): found.extend(references(s['steps']))
            if s['type'] == 'condition': found.extend(references(s['else_steps']))
        return found
    def control_steps(steps):
        found = []
        for s in steps:
            if s['type'] in ('executor', 'condition'):
                found.append(f"{s['name']} [{s['type']}: {s['ref']}]")
            if s['type'] in ('parallel', 'condition'):
                found.extend(control_steps(s['steps']))
            if s['type'] == 'condition':
                found.extend(control_steps(s['else_steps']))
        return found
    for key, flow in flows.items():
        description = flow['description'] + '\n靜態流程交接（前序 → 後續）：\n' + '\n'.join(f'{a} → {b}' for a,b in sorted(edges[key]))
        description += '\n控制閘道與執行步驟：\n' + '\n'.join('- ' + item for item in control_steps(flow['steps']))
        description += '\n圖中的 dependsOn 箭頭是後續對前序的依賴方向；平行步驟不代表彼此呼叫。實際委派及執行請查 Langfuse。'
        component(key, flow['name'], 'workflow', description, references(flow['steps']))
    config = {'version':'1.3.18','cache':True,'endpoints':{'custom':[{'name':'Agno',
        'apiKey':'${OS_SECURITY_KEY}','baseURL':'http://agno-gateway:8080/v1',
        'models':{'default':list(teams)+list(agents),'fetch':False},
        'headers':{'X-User-ID':'{{LIBRECHAT_USER_ID}}','X-Conversation-ID':'{{LIBRECHAT_BODY_CONVERSATIONID}}'},
        'titleConvo':False,'modelDisplayLabel':'Agno'}]}}
    return entities, config


def export(registry):
    root = Path(__file__).resolve().parent.parent
    entities, config = render(registry)
    dest = root / 'integration' / 'catalog'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'entities.yaml').write_text('\n---\n'.join(json.dumps(e, ensure_ascii=False, indent=2) for e in entities)+'\n', encoding='utf-8')
    (root / 'integration' / 'librechat.yaml').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Exported revision {registry['revision']}: {len(registry['agents'])} agents, {len(registry['teams'])} teams, {len(registry['workflows'])} workflows, {len(registry['skills'])} skills")

if __name__ == '__main__':
    export(load())
