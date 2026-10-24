RAIN-ROUTE TRANSFERABLE PYTHON MVP — 21 OCTOBER 2026

WHAT IS ACTUALLY WORKING
- Uses Python NetworkX to compute shortest paths, remove each graph edge once, retest all origins, compute ECI / ORI / SARI, count finite detours, and export complete matrix/audit.
- Accepts school-specific CSV edge and origin inputs; works with arbitrary eligible graph sizes within MVP limits.
- Includes one SYNTHETIC demonstration dataset to prove program logic.
- The Danao tab is an ARCHIVED RESULTS VIEW only. It is NOT an independent Danao graph rerun.
- NO AUTOMATIC SCHOOL-NAME GEOCODING OR ROAD MAPPING IN THIS VERSION.
- NOT DEPLOYED TO A PUBLIC WEBSITE BY THIS PACKAGE.

HOW TO RUN ON WINDOWS
1. Extract this folder.
2. Install Python 3.11+ (enable Add Python to PATH).
3. Open Windows PowerShell in this folder.
4. Run: python -m pip install -r requirements.txt
5. Run: python -m streamlit run app.py
6. Your browser opens the RAIN-ROUTE app, usually http://localhost:8501
7. Select 'Use clearly synthetic demonstration graph' then 'Run actual graph computation'.
8. Observe results 18 scenarios / 13 retained / 5 lost / SARI 72.22%. These are not research findings.
9. Download the matrix and JSON audit files.
10. To test a real school, untick synthetic demo and upload locally documented edge/origin CSVs.

HOW TO VERIFY ENGINE WITHOUT STREAMLIT
python tests/test_engine.py
Expected: PASS: 18 scenarios, 13 retained, 5 lost, SARI 72.22%, finite detour observed; graph is not tree

REQUIRED EDGE CSV: edge_id,source,target,weight_m
REQUIRED ORIGIN CSV: origin_id,node_id
School attachment node is entered in the UI. All attachments are treated as fixed. Origin and school attachment lengths can be added separately as constants to total route lengths; the MVP computes internal road length only.

CRITICAL SCIENTIFIC LIMITATIONS
- Missing or inaccurate roads can create spurious disconnections.
- Source roads must be verified and their graph version frozen.
- Multi-edge failures, real-time road conditions, flood and road-safety predictions are excluded.
- Reviewer signatures and independent geographic validation cannot be manufactured by software.
- To verify archived DTDMIS results, import the ORIGINAL frozen Danao graph and independently compare all 72 rows and numerical indices.
- Compostela OSM data remain preliminary until reviewed and eligible edge boundaries harmonized.
