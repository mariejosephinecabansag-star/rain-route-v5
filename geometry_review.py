"""Untrusted mapped-road geometry loader; display-only, no analytic graph mutations."""
import json,csv,io,math

class GeometryError(ValueError): pass

def _point(pt):
    if not isinstance(pt,(list,tuple)) or len(pt)<2: raise GeometryError('Coordinates must be [longitude,latitude] pairs')
    lon,lat=pt[:2]
    if not isinstance(lon,(float,int)) or not isinstance(lat,(float,int)) or not math.isfinite(lon) or not math.isfinite(lat) or abs(lon)>180 or abs(lat)>90: raise GeometryError('Invalid WGS84 longitude / latitude')
    return [float(lon),float(lat)]

def parse_edge_geojson(blob, allowed_edges, nodes, edges):
    if len(blob)>2_000_000: raise GeometryError('File exceeds 2 MB; upload a simplified road subset')
    try: o=json.loads(blob)
    except (ValueError,UnicodeDecodeError) as e: raise GeometryError('Invalid JSON') from e
    if not isinstance(o,dict) or o.get('type')!='FeatureCollection' or not isinstance(o.get('features'),list): raise GeometryError('Expected a GeoJSON FeatureCollection')
    if len(o['features'])>300: raise GeometryError('Too many features (300 max)')
    paths={}; alerts=[]
    allowed=set(allowed_edges)
    endpairs={e['edge_id']:(e['source'],e['target']) for e in edges}
    for f in o['features']:
        if not isinstance(f,dict) or f.get('type')!='Feature': raise GeometryError('Each item must be GeoJSON Feature')
        props=f.get('properties') or {}; k=props.get('edge_id')
        if k not in allowed: alerts.append('Skipped feature with unrecognized/missing edge_id');continue
        if k in paths: raise GeometryError('Duplicate road geometry for '+k)
        geometry=f.get('geometry') or {}
        if geometry.get('type')!='LineString': raise GeometryError(k+' must be a LineString')
        coords=geometry.get('coordinates')
        if not isinstance(coords,list) or len(coords)<2 or len(coords)>2500: raise GeometryError(k+' needs 2–2500 points')
        path=[_point(pt) for pt in coords]
        a,b=endpairs[k]
        # Distance in degrees; enough to flag implausible visual mismatch without rejecting geometry.
        d1=min(abs(path[0][0]-nodes[a]['lon'])+abs(path[0][1]-nodes[a]['lat']),abs(path[-1][0]-nodes[a]['lon'])+abs(path[-1][1]-nodes[a]['lat']))
        d2=min(abs(path[0][0]-nodes[b]['lon'])+abs(path[0][1]-nodes[b]['lat']),abs(path[-1][0]-nodes[b]['lon'])+abs(path[-1][1]-nodes[b]['lat']))
        if max(d1,d2)>0.002: alerts.append(k+' endpoints appear >~200 m from desk anchors; review snap/geometry')
        if not props.get('source'): alerts.append(k+' has no source citation')
        paths[k]=path
    return paths,alerts

def geometry_template(nodes,edges):
    out={'type':'FeatureCollection','name':'TEMPLATE_ONLY_NOT_VALIDATED','features':[]}
    for e in edges:
        a,b=nodes[e['source']],nodes[e['target']]
        out['features'].append({'type':'Feature','properties':{'edge_id':e['edge_id'],'source':'TEMPLATE ONLY — REPLACE WITH TRACEABLE SOURCE','verification':'NOT VERIFIED','reviewer':'','survey_date':''},'geometry':{'type':'LineString','coordinates':[[a['lon'],a['lat']],[b['lon'],b['lat']]]}})
    return json.dumps(out,indent=2)

def review_rows(edges,names,paths):
    out=io.StringIO();w=csv.writer(out)
    w.writerow(['edge_id','archived_road_label','geometry_supplied','data_source_url','source_date','school_gate_confirmed','both_endpoints_checked','road_traced_on_current_map','qualified_reviewer','review_date','review_decision','notes'])
    for e in edges: w.writerow([e['edge_id'],names.get(e['edge_id'],''),'YES' if e['edge_id'] in paths else 'NO','','','PENDING','PENDING','PENDING','','','UNVALIDATED',''])
    return out.getvalue()
