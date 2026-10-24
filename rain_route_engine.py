"""RAIN-ROUTE reusable, deterministic structural road-graph engine.
All results are scoped to the submitted frozen graph and selected origins.
"""
from __future__ import annotations
import csv, io, json, hashlib
from dataclasses import dataclass
from collections import defaultdict
from typing import List, Dict
import networkx as nx

REQUIRED_EDGES = ('edge_id','source','target','weight_m')
REQUIRED_ORIGINS = ('origin_id','node_id')

class InputError(ValueError): pass

def csv_rows(content: bytes, required):
    try:
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None: raise InputError('Empty CSV')
        fields = [x.strip() for x in reader.fieldnames]
        if not set(required).issubset(fields):
            raise InputError('Missing columns: '+', '.join(sorted(set(required)-set(fields))))
        rows = [{str(k).strip(): (v or '').strip() for k,v in row.items()} for row in reader]
        if not rows: raise InputError('CSV has no data rows')
        return rows
    except UnicodeDecodeError as e:
        raise InputError('CSV must be UTF-8') from e


def analyze(edges: List[dict], origins: List[dict], school_node: str, school_name: str='Unnamed school') -> Dict:
    if not school_node.strip(): raise InputError('School attachment node is required')
    if len(edges)>1500 or len(origins)>100: raise InputError('For responsive MVP use up to 1500 edges and 100 origins')
    g=nx.Graph()
    ids=set()
    for r in edges:
        try:
            edge_id=r['edge_id'].strip(); u=r['source'].strip(); v=r['target'].strip()
            w=float(r['weight_m'])
        except (KeyError,ValueError,TypeError) as e: raise InputError('Invalid edges columns or weights') from e
        if not edge_id or not u or not v: raise InputError('All edge identifiers and endpoints must be provided')
        if edge_id in ids: raise InputError(f'Duplicate edge_id: {edge_id}')
        if u==v: raise InputError(f'Self-loop unsupported: {edge_id}')
        if not (0<w<float('inf')): raise InputError(f'Weight must be positive finite: {edge_id}')
        if g.has_edge(u,v): raise InputError(f'Parallel edge endpoints unsupported in undirected MVP: {u}-{v}')
        ids.add(edge_id);g.add_edge(u,v,weight=w,edge_id=edge_id)
    if school_node not in g: raise InputError(f'School attachment node {school_node} is not in edge graph')
    origin_ids=set()
    for r in origins:
        name=r.get('origin_id','').strip(); node=r.get('node_id','').strip()
        if not name or not node: raise InputError('Origin names and nodes cannot be empty')
        if name in origin_ids: raise InputError('Duplicate origin_id: '+name)
        if node not in g: raise InputError(f'Origin {name} attachment node {node} absent from graph')
        origin_ids.add(name)
    ordered_edges=sorted(ids)
    ordered_origins=sorted(origins,key=lambda r:r['origin_id'])
    d0=nx.single_source_dijkstra_path_length(g,school_node,weight='weight')
    missing=[o['origin_id'] for o in ordered_origins if o['node_id'] not in d0]
    if missing: raise InputError('All baseline origins must reach school; disconnected origins: '+', '.join(missing))
    baseline=[]
    for o in ordered_origins:
        n=o['node_id']; path=nx.shortest_path(g,n,school_node,weight='weight')
        baseline.append({'origin_id':o['origin_id'],'node_id':n,'baseline_internal_distance_m':round(d0[n],3),
                         'baseline_node_path':' > '.join(path)})
    results=[]
    for e in sorted(edges,key=lambda x:x['edge_id']):
        edge_id=e['edge_id']; u=e['source'];v=e['target'];attrs=g[u][v].copy()
        g.remove_edge(u,v)
        dist=nx.single_source_dijkstra_path_length(g,school_node,weight='weight')
        for o in ordered_origins:
            orig=o['origin_id'];node=o['node_id'];ret=int(node in dist)
            detour=(dist[node]-d0[node]) if ret else None
            if detour is not None and detour < -1e-7: raise AssertionError('Edge removal reduced a shortest path')
            results.append({'origin_id':orig,'removed_edge':edge_id,'access_retained':ret,
                'baseline_internal_distance_m':round(d0[node],3),
                'disrupted_internal_distance_m':round(dist[node],3) if ret else '',
                'finite_detour_m':round(max(0,detour),3) if ret else '',
                'status':'RETAINED' if ret else 'ACCESS LOST'})
        g.add_edge(u,v,**attrs)
    ec=[];orr=[]
    for edge_id in ordered_edges:
        selected=[r for r in results if r['removed_edge']==edge_id]
        lost=sum(1-r['access_retained'] for r in selected)
        ec.append({'edge_id':edge_id,'origins_lost':lost,'eci_pct':round(lost/len(origins)*100,2)})
    for o in ordered_origins:
        selected=[r for r in results if r['origin_id']==o['origin_id']]
        kept=sum(r['access_retained'] for r in selected)
        orr.append({'origin_id':o['origin_id'],'retained':kept,'ori_pct':round(kept/len(edges)*100,2)})
    retained=sum(r['access_retained'] for r in results)
    model={'school_name':school_name,'school_node':school_node,'edges':edges,'origins':origins}
    digest=hashlib.sha256(json.dumps(model,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {'school_name':school_name,'school_node':school_node,'graph_sha256':digest,
        'node_count':g.number_of_nodes(),'edge_count':g.number_of_edges(),'origin_count':len(origins),
        'connected_internal_graph':nx.is_connected(g), 'internal_graph_is_tree':nx.is_tree(g),
        'baseline':baseline,'matrix':results,'eci':ec,'ori':orr,
        'scenario_count':len(results),'retained':retained,'lost':len(results)-retained,
        'sari_pct':round(retained/len(results)*100,2),
        'positive_finite_detours':sum(1 for r in results if r['finite_detour_m']!='' and r['finite_detour_m']>1e-7),
        'data_status':'USER-SUPPLIED / NOT INDEPENDENTLY GEOGRAPHICALLY VALIDATED'}


def to_csv(rows):
    if not rows: return ''
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
    return output.getvalue()
