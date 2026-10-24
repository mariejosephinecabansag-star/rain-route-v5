"""RAIN-ROUTE V5: interactive geographic reference and reviewed road-geometry imports."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
import networkx as nx
import pydeck as pdk
from geometry_review import parse_edge_geojson, geometry_template, review_rows, GeometryError
from rain_route_engine import analyze, csv_rows, InputError, to_csv, REQUIRED_EDGES, REQUIRED_ORIGINS

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
st.set_page_config(page_title='RAIN-ROUTE | School Access Network Lab',page_icon='🛣️',layout='wide')
st.title('🛣️ RAIN-ROUTE | School Access Network Lab V5')
st.caption('Configurable Python graph-analysis prototype • Single-edge disruption • ECI / ORI / SARI')
st.warning('RESEARCH SCREENING ONLY. Not a flood prediction, road-safety certification, evacuation planner, or a live road map. Geographic validation remains separate.')

def load_sample(name):
    e=csv_rows((DATA/f'{name}_edges.csv').read_bytes(), REQUIRED_EDGES)
    o=csv_rows((DATA/f'{name}_origins.csv').read_bytes(), REQUIRED_ORIGINS)
    return e,o

def network_dot(edges, origins, school_node, highlight=None):
    """Structural connectivity schematic. Positions are deliberately not geographic."""
    graph=nx.Graph()
    for e in edges: graph.add_edge(e['source'],e['target'],edge_id=e['edge_id'])
    origin_nodes={o['node_id'] for o in origins}
    lines=['graph R {','graph [rankdir=LR, overlap=false, splines=polyline, nodesep=0.18, ranksep=0.3, pad=0.1, outputorder=edgesfirst, bgcolor="transparent"];',
           'node [shape=circle, fixedsize=true, width=0.58, height=0.58, fontsize=10, style=filled, fillcolor="#eaf2ff", color="#385e96", fontname="Arial"];',
           'edge [fontname="Arial", fontsize=9, color="#7e8ba0", arrowsize=0.4];']
    for node in graph.nodes:
        fill='#ffdf9a' if node==school_node else ('#d6f4e8' if node in origin_nodes else '#eaf2ff')
        lines.append(f'"{node}" [fillcolor="{fill}"];')
    for e in edges:
        col='#c2413b' if highlight == e['edge_id'] else '#8191a7'
        thick='3.8' if highlight == e['edge_id'] else '1.7'
        lines.append(f'"{e["source"]}" -- "{e["target"]}" [label="{e["edge_id"]}", color="{col}", penwidth={thick}];')
    lines.append('}')
    return '\n'.join(lines)

mode=st.radio('Choose dataset', ['DTDMIS — archived analytical input', 'Another school — upload CSVs', 'Synthetic tutorial graph'], horizontal=True)
mode_key={'DTDMIS — archived analytical input':'danao','Another school — upload CSVs':'upload','Synthetic tutorial graph':'demo'}[mode]
with st.expander('Dataset and validation rules',expanded=False):
    st.write('DTDMIS: archived secondary-data analytical graph; Python computation reproduced, independent geographical review pending. Another school: user-supplied CSVs are **not validated by uploading them**. Synthetic mode: testing and training only.')
    st.write('Only tested internal edges appear in the CSV. School and origin attachments are represented by fixed node associations, **not** separately tested edges. Weights are nonnegative computational distance proxies, not surveyed route measurements.')
    a,b=st.columns(2)
    a.download_button('Example edges CSV',(DATA/'DEMO_SYNTHETIC_edges.csv').read_bytes(),'SAMPLE_edges.csv',mime='text/csv')
    b.download_button('Example origins CSV',(DATA/'DEMO_SYNTHETIC_origins.csv').read_bytes(),'SAMPLE_origins.csv',mime='text/csv')

if mode_key=='danao':
    school_name='D.T. Durano Memorial Integrated School'
    school_node='N04'
    edges,origins=load_sample('DANAO_FINAL')
    st.info('Archived Danao analytical inputs loaded. Recompute them to verify the manuscript values. This does not independently validate the real-world road topology.')
elif mode_key=='demo':
    school_name='Synthetic tutorial network (NOT real geography)'
    school_node='S'
    edges,origins=load_sample('DEMO_SYNTHETIC')
    st.info('This is a fabricated tutorial graph for software behavior only.')
else:
    left,right=st.columns(2)
    with left:
        school_name=st.text_input('School name',value='New school network')
        edge_upload=st.file_uploader('Internal road edges CSV',type=['csv'],key='edges_v2')
    with right:
        school_node=st.text_input('Confirmed internal school attachment node',value='')
        origins_upload=st.file_uploader('Community-origin attachment CSV',type=['csv'],key='origins_v2')
    edges=origins=None
    if edge_upload is not None and origins_upload is not None:
        try:
            edges=csv_rows(edge_upload.getvalue(),REQUIRED_EDGES)
            origins=csv_rows(origins_upload.getvalue(),REQUIRED_ORIGINS)
        except InputError as ex: st.error(f'Input problem: {ex}')
    st.caption('Required edges columns: edge_id, source, target, weight_m. Origins columns: origin_id, node_id. School names are descriptive; the engine does not automatically map roads.')

if edges and origins:
    st.write(f'**Network:** {len(edges)} tested edges; {len(origins)} origins; school attachment: `{school_node or "not entered"}`')
    with st.expander('Inspect input records'):
        l,r=st.columns(2)
        l.dataframe(pd.DataFrame(edges),hide_index=True,use_container_width=True)
        r.dataframe(pd.DataFrame(origins),hide_index=True,use_container_width=True)

if st.button('▶ Recompute all single-edge scenarios',type='primary',disabled=not (edges and origins and school_node)):
    try:
        result=analyze(edges,origins,school_node,school_name)
        st.session_state['v2result']=result
        st.session_state['v2edges']=edges
        st.session_state['v2origins']=origins
        st.session_state['v2mode']=mode_key
    except (InputError,ValueError) as ex:
        st.error(f'Analysis could not run: {ex}')

if 'v2result' in st.session_state:
    result=st.session_state['v2result']
    loaded_edges=st.session_state['v2edges']
    loaded_origins=st.session_state['v2origins']
    source_mode=st.session_state['v2mode']
    if source_mode != mode_key:
        st.info('Results below belong to the previously run dataset. Press Recompute to analyze the currently selected dataset.')
    st.subheader('Computational results')
    a,b,c,d=st.columns(4)
    a.metric('Total scenarios',result['scenario_count']); b.metric('Retained',result['retained']); c.metric('Lost',result['lost']); d.metric('SARI',f"{result['sari_pct']:.2f}%")
    st.caption(f"Nodes: {result['node_count']} • Edges: {result['edge_count']} • Origins: {result['origin_count']} • Connected: {result['connected_internal_graph']} • Tree: {result['internal_graph_is_tree']} • Finite detours: {result['positive_finite_detours']}")
    if result['internal_graph_is_tree']:
        st.info('Tree topology: there is exactly one internal path between any two nodes. Removal of a path edge causes disconnection, not a finite alternative detour. Real roads outside the graph may exist.')
    elif result['positive_finite_detours']:
        st.info('Some tested edge removals retain access by an alternate internal route with increased modeled distance.')
    if source_mode=='danao':
        passed=(result['scenario_count']==72 and result['retained']==59 and result['lost']==13 and result['sari_pct']==81.94
                and result['positive_finite_detours']==0 and result['internal_graph_is_tree']
                and next(x['eci_pct'] for x in result['eci'] if x['edge_id']=='E07')==50.0
                and next(x['ori_pct'] for x in result['ori'] if x['origin_id']=='O3')==66.67)
        (st.success if passed else st.error)('Danao manuscript numeric check: '+('PASS — reproduced frozen results' if passed else 'MISMATCH — investigate before using results'))
    geo_tab, graph_tab, index_tab, matrix_tab, audit_tab=st.tabs(['Geographic reference view','Interactive edge test','Indices and baseline','72-case / full scenario matrix','Audit and exports'])
    with geo_tab:
        st.subheader('Danao road-geometry evidence workspace')
        st.warning('PROVISIONAL MAPPING — Archived desk coordinates are not surveyed. Map lines are straight references unless a user uploads a source-documented GeoJSON; uploads are not automatically validated. N04 is a modeled school attachment, NOT a verified gate.')
        if source_mode != 'danao':
            st.info('The uploaded/synthetic graph has no verified coordinate dataset bundled with this app. Use its structural diagram instead. Do not use Danao coordinates for another school.')
        else:
            geo_data=json.loads((DATA/'DANAO_DESK_COORDINATES_PROVISIONAL.json').read_text(encoding='utf-8'))
            geo_nodes=geo_data['nodes']
            geo_edges=geo_data['edge_names']
            edge_ids=[e['edge_id'] for e in loaded_edges]
            geo_choice_key='v4_geo_focus_'+result['graph_sha256']
            if geo_choice_key not in st.session_state or st.session_state[geo_choice_key] not in edge_ids:
                st.session_state[geo_choice_key]='E07' if 'E07' in edge_ids else edge_ids[0]
            geo_left,geo_right=st.columns([2.5,1],gap='medium')
            with geo_right:
                geo_focus=st.selectbox('Simulated blocked edge',edge_ids,key=geo_choice_key)
                geo_affected=[r['origin_id'] for r in result['matrix'] if r['removed_edge']==geo_focus and r['access_retained']==0]
                geo_retained=[r['origin_id'] for r in result['matrix'] if r['removed_edge']==geo_focus and r['access_retained']==1]
                geo_stat=next(v for v in result['eci'] if v['edge_id']==geo_focus)
                st.metric('ECI',f"{geo_stat['eci_pct']:.2f}%")
                if geo_affected:
                    st.error('Access lost: ' + ', '.join(geo_affected))
                else:
                    st.success('No access losses for this removal')
                st.success('Access retained: '+(', '.join(geo_retained) if geo_retained else 'none'))
                st.caption('Selection changes the displayed result; it does not physically block a real road.')
                st.caption('Road name (archived): '+geo_edges.get(geo_focus,'not recorded'))
                st.download_button('Download node-coordinate evidence JSON',json.dumps(geo_data,indent=2),file_name='DANAO_PROVISIONAL_COORDINATES.json',mime='application/json')
            # Optional road traces, matched strictly to E01-E12; display-only, never input to numerical engine.
            st.markdown('**Road geometry evidence — optional**')
            st.caption('Upload a GeoJSON FeatureCollection of LineString features. Each feature must have properties.edge_id = an existing E01–E12 ID. The reviewer must confirm the mapping before the lines are presented as geographically validated. Geometry never changes the frozen Danao calculations.')
            trace_file=st.file_uploader('Road geometry GeoJSON (provisional / reviewed)', type=['geojson','json'],key='v5_geojson')
            reviewed_paths={}
            geometry_errors=[]
            if trace_file is not None:
                try:
                    reviewed_paths,geometry_errors=parse_edge_geojson(trace_file.getvalue(),edge_ids,geo_nodes,loaded_edges)
                    if reviewed_paths:
                        st.success(f'{len(reviewed_paths)}/{len(edge_ids)} road polylines loaded for display only; geographic status remains unvalidated until separately reviewed.')
                    if geometry_errors:
                        st.warning('Geometry review flags: ' + '; '.join(geometry_errors[:5]))
                except GeometryError as exc:
                    st.error(f'Cannot use geometry file: {exc}')
            with st.expander('Evidence instructions and geometry review CSV'):
                st.caption('Expected coordinate order is [longitude, latitude] in WGS84 (EPSG:4326). Provide a source URL, date, reviewer, and supporting road-match evidence for every E-ID. No uploaded line becomes validated automatically.')
                st.download_button('Download GeoJSON example (provisional straight segments)',geometry_template(geo_nodes,loaded_edges),'DANAO_GEOMETRY_TEMPLATE_UNVALIDATED.geojson',mime='application/geo+json')
                st.download_button('Download geometry review checklist CSV',review_rows(loaded_edges,geo_edges,reviewed_paths),'DANAO_GEOMETRY_REVIEW_CHECKLIST.csv',mime='text/csv')
            highlighted=[]
            for e in loaded_edges:
                a=geo_nodes[e['source']]; b=geo_nodes[e['target']]
                route_path=reviewed_paths.get(e['edge_id'], [[a['lon'],a['lat']],[b['lon'],b['lat']]])
                highlighted.append({'edge_id':e['edge_id'],'road_label':geo_edges.get(e['edge_id'],''),
                  'path':route_path,'geometry_status':('UPLOADED - PENDING INDEPENDENT CHECK' if e['edge_id'] in reviewed_paths else 'STRAIGHT-LINE REFERENCE'),
                  'color':[204,58,55,245] if e['edge_id']==geo_focus else [61,112,170,170],
                  'width':9 if e['edge_id']==geo_focus else 4})
            marker_nodes=[]
            origin_node_ids={o['node_id'] for o in loaded_origins}
            for nid,node in geo_nodes.items():
                marker_nodes.append({'node_id':nid,'description':node['description'],
                 'lat':node['lat'],'lon':node['lon'],'coordinate_status':node['coordinate_status'],
                 'fill':[246,182,65,240] if nid==result['school_node'] else ([50,165,125,235] if nid in origin_node_ids else [69,113,170,220]),
                 'radius':10 if nid==result['school_node'] else 7})
            layers=[
                pdk.Layer('PathLayer',data=highlighted,get_path='path',get_color='color',get_width='width',width_min_pixels=3,pickable=True,id='reference_edges'),
                pdk.Layer('ScatterplotLayer',data=marker_nodes,get_position='[lon,lat]',get_radius=25,radius_min_pixels=6,radius_max_pixels=11,get_fill_color='fill',pickable=True,id='reference_nodes'),
                pdk.Layer('TextLayer',data=marker_nodes,get_position='[lon,lat]',get_text='node_id',get_size=12,get_color=[20,29,45,250],get_pixel_offset=[0,-16],pickable=False,id='reference_labels')]
            middle_lat=sum(n['lat'] for n in geo_nodes.values())/len(geo_nodes)
            middle_lon=sum(n['lon'] for n in geo_nodes.values())/len(geo_nodes)
            view=pdk.ViewState(latitude=middle_lat,longitude=middle_lon,zoom=14.3,pitch=0)
            deck=pdk.Deck(layers=layers,initial_view_state=view,map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
                tooltip={'html':'<b>{edge_id}{node_id}</b><br/>{road_label}{description}<br/>{geometry_status}{coordinate_status}', 'style':{'backgroundColor':'#243047','color':'white'}},
                height=520)
            with geo_left:
                selected_map = st.pydeck_chart(deck, width='stretch', on_select='rerun', selection_mode='single-object', key='v5_danao_map')
                selected_objects = selected_map.get('selection',{}).get('objects',{}).get('reference_edges',[])
                if selected_objects:
                    chosen = selected_objects[0].get('edge_id')
                    if chosen in edge_ids and chosen != geo_focus:
                        st.session_state[geo_choice_key] = chosen
                        st.rerun()
                st.caption('Map tiles require internet. Unless a documented GeoJSON geometry is uploaded, connections are straight provisional node-to-node lines. Displayed map lines do not establish route validity.')
            st.info('Click a road line to select an E01–E12 scenario. This selects an EXISTING coded edge only. A map click does not confirm its true location or block an actual road.')
            with st.expander('Coordinate and evidence inventory'):
                st.dataframe(pd.DataFrame(marker_nodes)[['node_id','description','lat','lon','coordinate_status']],hide_index=True,use_container_width=True)
    with graph_tab:
        st.caption('Select a road using its **edge tile** (E01–E12). The drawing highlights the chosen connection. The diagram lines themselves are not clickable; this is NOT a geographic map.')
        edge_ids=[e['edge_id'] for e in loaded_edges]
        chosen_key=f"v3_selected_edge_{result['graph_sha256']}"
        if chosen_key not in st.session_state or st.session_state[chosen_key] not in edge_ids:
            st.session_state[chosen_key]='E07' if 'E07' in edge_ids else edge_ids[0]
        focus=st.session_state[chosen_key]
        map_col,details_col=st.columns([2.05,1],gap='medium')
        with details_col:
            st.markdown('**Select blocked road**')
            # Real native Streamlit controls: reliably clickable without browser scripts.
            for start in range(0,len(edge_ids),3):
                group=st.columns(3,gap='small')
                for col,edge_id in zip(group,edge_ids[start:start+3]):
                    if col.button(edge_id,key=f"v3_btn_{result['graph_sha256']}_{edge_id}",use_container_width=True,
                                  type='primary' if focus==edge_id else 'secondary'):
                        st.session_state[chosen_key]=edge_id
                        st.rerun()
            affected=[r['origin_id'] for r in result['matrix'] if r['removed_edge']==focus and r['access_retained']==0]
            retained_origins=[r['origin_id'] for r in result['matrix'] if r['removed_edge']==focus and r['access_retained']==1]
            edge_stat=next(r for r in result['eci'] if r['edge_id']==focus)
            st.markdown(f'#### Scenario: {focus} removed')
            st.metric('Edge Criticality Index',f"{edge_stat['eci_pct']:.2f}%")
            if affected:
                st.error('ACCESS LOST: ' + ', '.join(affected))
            else:
                st.success('No origins lose modeled access')
            st.success('ACCESS RETAINED: '+(', '.join(retained_origins) if retained_origins else 'None')) if retained_origins else st.warning('No origins retain modeled access')
            st.caption(f"{len(affected)} of {len(loaded_origins)} declared origins lose modeled access when {focus} is removed. Results come from the computed scenario matrix, not manual labels.")
        with map_col:
            st.graphviz_chart(network_dot(loaded_edges,loaded_origins,result['school_node'],focus),use_container_width=True)
            st.caption('Red line = selected tested edge; yellow = school attachment; green = origin attachment nodes. Layout is schematic, not real road geometry.')
        st.markdown('**Origin outcomes for the selected edge**')
        st.dataframe(pd.DataFrame([{'origin':r['origin_id'],'result':r['status']} for r in result['matrix'] if r['removed_edge']==focus]),hide_index=True,use_container_width=True)
    with index_tab:
        x,y=st.columns(2)
        with x: st.write('**ECI — origin losses per removed edge**');st.dataframe(pd.DataFrame(result['eci']),hide_index=True,use_container_width=True)
        with y: st.write('**ORI — scenarios retained per origin**');st.dataframe(pd.DataFrame(result['ori']),hide_index=True,use_container_width=True)
        st.write('**Baseline internal-graph paths**')
        st.dataframe(pd.DataFrame(result['baseline']),hide_index=True,use_container_width=True)
        st.caption('Baseline values exclude fixed origin and school attachment distances; do not compare them directly with total proxy distances in the manuscript.')
    with matrix_tab:
        matrix=pd.DataFrame(result['matrix']);st.dataframe(matrix,hide_index=True,use_container_width=True)
        pivot=matrix.pivot(index='origin_id',columns='removed_edge',values='access_retained')
        st.write('**Access matrix** — 1 = retained; 0 = lost');st.dataframe(pivot,use_container_width=True)
    with audit_tab:
        st.write('**Graph fingerprint**');st.code(result['graph_sha256'])
        st.write(f"Consistency: {result['retained']} retained + {result['lost']} lost = {result['scenario_count']} tested scenarios")
        st.download_button('Download full disruption matrix CSV',to_csv(result['matrix']),'rain_route_matrix.csv',mime='text/csv')
        st.download_button('Download ECI CSV',to_csv(result['eci']),'rain_route_eci.csv',mime='text/csv')
        st.download_button('Download ORI CSV',to_csv(result['ori']),'rain_route_ori.csv',mime='text/csv')
        st.download_button('Download full JSON audit',json.dumps(result,indent=2),'rain_route_audit.json',mime='application/json')
        st.download_button('Download input edges CSV',to_csv(loaded_edges),'rain_route_input_edges.csv',mime='text/csv')
        st.download_button('Download input origins CSV',to_csv(loaded_origins),'rain_route_input_origins.csv',mime='text/csv')
        st.caption('These files establish reproducibility for the submitted analytical graph; they are not geographic validation or official road-safety evidence.')

st.divider()
st.caption('RAIN-ROUTE V5 • Research prototype • Each independently mapped school requires its own validated graph, school gate, origin anchors and recorded boundary before real-world interpretation.')
