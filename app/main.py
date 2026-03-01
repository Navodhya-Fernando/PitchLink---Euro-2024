"""
EURO 2024 Network Explorer - Command Center Dashboard
Single-Page Professional Sports Analytics Interface
"""
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (Select, Slider, TextInput, Button, Div, CustomJS, 
                          HoverTool, ColumnDataSource)
from bokeh.plotting import figure
from py2neo import Graph
import os
from dotenv import load_dotenv
import networkx as nx

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

graph = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# ========== PLAYER INTELLIGENCE QUERIES ==========
def get_player_intel(player_name):
    """Fetch tactical intelligence for a specific player"""
    try:
        # Get player details
        player_query = """
        MATCH (p:Player {name: $name})-[:PLAYS_FOR]->(t:Team)
        RETURN p.name AS name, t.name AS team, p.position AS position,
               p.betweenness AS centrality, p.pagerank AS influence,
               p.in_degree AS receptions, p.out_degree AS passes
        """
        player = graph.run(player_query, name=player_name).data()
        if not player:
            return None
        
        player = player[0]
        
        # Get top passes TO (recipients)
        passed_to_query = """
        MATCH (p1:Player {name: $name})-[r:PASSED_TO]->(p2:Player)
        RETURN p2.name AS partner, r.weight AS volume
        ORDER BY volume DESC LIMIT 5
        """
        passed_to = graph.run(passed_to_query, name=player_name).data()
        
        # Get top passes FROM (sources)
        passed_from_query = """
        MATCH (p1:Player)-[r:PASSED_TO]->(p2:Player {name: $name})
        RETURN p1.name AS partner, r.weight AS volume
        ORDER BY volume DESC LIMIT 5
        """
        passed_from = graph.run(passed_from_query, name=player_name).data()
        
        return {
            'player': player,
            'passed_to': passed_to,
            'passed_from': passed_from
        }
    except Exception as e:
        print(f"Error fetching player intel: {e}")
        return None

def get_team_leaders(team_name):
    """Fetch tactical leaders for a specific team"""
    try:
        leaders_query = """
        MATCH (p:Player)-[:PLAYS_FOR]->(t:Team {name: $team})
        RETURN p.name AS player, 
               p.betweenness AS playmaker,
               p.pagerank AS influence,
               p.in_degree AS target_score
        ORDER BY playmaker DESC LIMIT 3
        """
        leaders = graph.run(leaders_query, team=team_name).data()
        return leaders
    except Exception as e:
        print(f"Error fetching team leaders: {e}")
        return []

# ========== DATA LOADING ==========
def load_network_data():
    """Load complete passing network from Neo4j"""
    
    players_query = """
    MATCH (p:Player)-[:PLAYS_FOR]->(t:Team)
    RETURN p.name AS name, p.position AS position, t.name AS team,
           p.betweenness AS centrality, p.pagerank AS pagerank,
           p.x AS x, p.y AS y
    """
    players = graph.run(players_query).data()
    
    edges_query = """
    MATCH (p1:Player)-[r:PASSED_TO]->(p2:Player)
    RETURN p1.name AS source, p2.name AS target, r.weight AS weight
    """
    edges = graph.run(edges_query).data()
    
    G = nx.DiGraph()
    for p in players:
        G.add_node(p['name'], **p)
    for e in edges:
        G.add_edge(e['source'], e['target'], weight=e['weight'])
    
    pos = nx.spring_layout(G, k=3, iterations=100, seed=42)
    
    node_data = {
        'name': [], 'x': [], 'y': [], 'size': [], 'base_size': [], 'current_size': [],
        'color': [], 'alpha': [], 'base_alpha': [], 'team': [], 'position': [],
        'centrality': [], 'pagerank': []
    }
    
    team_colors = {
        'Spain': '#ff1744', 'England': '#2196f3', 'France': '#1976d2',
        'Netherlands': '#ff6f00', 'Germany': '#4caf50', 'Portugal': '#e91e63',
        'Switzerland': '#f44336', 'Turkey': '#9c27b0'
    }
    
    for p in players:
        name = p['name']
        # Scale positions to larger canvas area (multiply by larger factor for visibility)
        x_pos = pos[name][0] * 200 if pos[name][0] else 0
        y_pos = pos[name][1] * 200 if pos[name][1] else 0
        node_data['name'].append(name)
        node_data['x'].append(p.get('x') or x_pos)
        node_data['y'].append(p.get('y') or y_pos)
        
        centrality = p.get('centrality', 0) or 0
        size = max(12, min(40, 15 + centrality * 500))
        node_data['size'].append(size)
        node_data['base_size'].append(size)
        node_data['current_size'].append(size)
        node_data['color'].append(team_colors.get(p['team'], '#ffffff'))
        node_data['alpha'].append(0.9)
        node_data['base_alpha'].append(0.9)
        node_data['team'].append(p['team'])
        node_data['position'].append(p.get('position', 'Unknown'))
        node_data['centrality'].append(centrality)
        node_data['pagerank'].append(p.get('pagerank', 0) or 0)
    
    edge_data = {
        'x0': [], 'y0': [], 'x1': [], 'y1': [], 'weight': [],
        'alpha': [], 'base_alpha': [], 'width': [], 'source': [], 'target': [],
        'passer': [], 'recipient': []
    }
    
    node_positions = {node_data['name'][i]: (node_data['x'][i], node_data['y'][i]) 
                      for i in range(len(node_data['name']))}
    
    for e in edges:
        if e['source'] in node_positions and e['target'] in node_positions:
            x0, y0 = node_positions[e['source']]
            x1, y1 = node_positions[e['target']]
            weight = e['weight']
            
            edge_data['x0'].append(x0)
            edge_data['y0'].append(y0)
            edge_data['x1'].append(x1)
            edge_data['y1'].append(y1)
            edge_data['weight'].append(weight)
            base_alpha = min(0.05 + weight * 0.002, 0.3)
            edge_data['alpha'].append(base_alpha)
            edge_data['base_alpha'].append(base_alpha)
            edge_data['width'].append(max(0.5, min(3, weight * 0.15)))
            edge_data['source'].append(e['source'])
            edge_data['target'].append(e['target'])
            edge_data['passer'].append(e['source'])
            edge_data['recipient'].append(e['target'])
    
    return node_data, edge_data, list(set([p['team'] for p in players]))

node_data, edge_data, teams = load_network_data()
nodes_source = ColumnDataSource(data=node_data)
edges_source = ColumnDataSource(data=edge_data)

# ========== VISUALIZATION ==========

header = Div(text="""
<div style="background: #111; padding: 20px 32px; border-bottom: 1px solid #1a1a1a;">
    <div style="max-width: 1800px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 16px;">
            <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #00ff41, #00d4ff); 
                border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px;">⚽</div>
            <div>
                <h1 style="color: #fff; margin: 0; font-size: 24px; font-weight: 700;">Euro 2024 Network</h1>
                <p style="color: #888; margin: 2px 0 0 0; font-size: 13px;">Neo4j Graph Visualization</p>
            </div>
        </div>
        <div style="padding: 8px 16px; background: #00ff41; border-radius: 6px;">
            <span style="color: #000; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">● LIVE</span>
        </div>
    </div>
</div>
""", sizing_mode="stretch_width", height=100)

plot = figure(
    width=1400, height=800, title="", tools="pan,wheel_zoom,tap,reset",
    active_scroll="wheel_zoom", background_fill_color="#0a0a0a",
    border_fill_color="#1a1a1a", outline_line_color="#222",
    sizing_mode="stretch_both",
    x_range=(-250, 250),  # Explicit range for scaled coordinates
    y_range=(-250, 250)   # Explicit range for scaled coordinates
)

edge_renderer = plot.segment(x0='x0', y0='y0', x1='x1', y1='y1', 
                             line_width='width', line_alpha='alpha', 
                             line_color='#00d4ff', source=edges_source)

node_renderer = plot.circle(x='x', y='y', size='current_size', 
                            fill_color='color', fill_alpha='alpha',
                            line_color='white', line_width=2,
                            source=nodes_source)

plot.xaxis.visible = False
plot.yaxis.visible = False
plot.xgrid.visible = False
plot.ygrid.visible = False

hover = HoverTool(tooltips=[
    ("Player", "@name"), ("Team", "@team"), ("Position", "@position"),
    ("Importance", "@centrality{0.0000}"), ("Influence", "@pagerank{0.0000}")
], renderers=[node_renderer])
plot.add_tools(hover)

# ========== CONTROLS ==========

# Team Filter
team_select = Select(
    title="Filter by Team",
    value="All",
    options=["All"] + sorted(teams),
    width=280,
    height=50
)

# Centrality Threshold
centrality_slider = Slider(
    title="Minimum Importance",
    start=0,
    end=0.05,
    value=0,
    step=0.001,
    width=280
)

# Edge Strength Threshold
edge_weight_slider = Slider(
    title="Minimum Pass Weight",
    start=1,
    end=20,
    value=1,
    step=1,
    width=280
)

# Player Search
player_search = TextInput(
    title="Search Player",
    placeholder="Type player name...",
    width=280
)

# Reset Button
reset_btn = Button(
    label="Reset View",
    button_type="success",
    width=280,
    height=40
)

# Info Panel
info_panel = Div(text="""
<div style="background: #1a1a1a; padding: 24px; border-radius: 12px; border: 1px solid #222;">
    <h3 style="color: #00ff41; margin: 0 0 20px 0; font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
        Controls
    </h3>
    <div style="color: #ccc; font-size: 13px; line-height: 2.2;">
        <div style="margin-bottom: 12px; padding: 14px; background: #111; border-radius: 8px; border-left: 3px solid #00ff41;">
            <strong style="color: #fff; font-weight: 600;">Zoom:</strong> Scroll wheel
        </div>
        <div style="margin-bottom: 12px; padding: 14px; background: #111; border-radius: 8px; border-left: 3px solid #00ff41;">
            <strong style="color: #fff; font-weight: 600;">Pan:</strong> Click & drag
        </div>
        <div style="margin-bottom: 12px; padding: 14px; background: #111; border-radius: 8px; border-left: 3px solid #00ff41;">
            <strong style="color: #fff; font-weight: 600;">Info:</strong> Hover nodes
        </div>
        <div style="margin-bottom: 12px; padding: 14px; background: #111; border-radius: 8px; border-left: 3px solid #00ff41;">
            <strong style="color: #fff; font-weight: 600;">Focus:</strong> Click node to highlight links
        </div>
        <div style="padding: 14px; background: #111; border-radius: 8px; border-left: 3px solid #00ff41;">
            <strong style="color: #fff; font-weight: 600;">Size:</strong> Player importance
        </div>
    </div>
    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #222;">
        <p style="color: #888; margin: 0; font-size: 11px; line-height: 1.8;">
            <strong style="color: #00ff41; display: block; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Dataset</strong>
            Euro 2024 Tournament<br>
            Players = Nodes<br>
            Passes = Edges
        </p>
    </div>
</div>
""", width=280, height=440)

# Statistics Panel
stats_query = f"""
MATCH (p:Player) WITH count(p) AS players
MATCH ()-[r:PASSED_TO]->() WITH players, count(r) AS passes
MATCH (t:Team) WITH players, passes, count(t) AS teams
RETURN players, passes, teams
"""
stats = graph.run(stats_query).data()[0]

stats_panel = Div(text=f"""
<div style="background: #1a1a1a; padding: 24px; border-radius: 12px; border: 1px solid #222;">
    <h3 style="color: #00ff41; margin: 0 0 20px 0; font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
        Network Stats
    </h3>
    <div style="display: grid; gap: 16px;">
        <div style="background: #111; padding: 20px; border-radius: 8px; border-left: 3px solid #00ff41;">
            <div style="color: #00ff41; font-size: 32px; font-weight: 800; margin-bottom: 4px;">{stats['players']}</div>
            <div style="color: #888; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Players</div>
        </div>
        <div style="background: #111; padding: 20px; border-radius: 8px; border-left: 3px solid #00ff41;">
            <div style="color: #00ff41; font-size: 32px; font-weight: 800; margin-bottom: 4px;">{stats['passes']}</div>
            <div style="color: #888; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Connections</div>
        </div>
        <div style="background: #111; padding: 20px; border-radius: 8px; border-left: 3px solid #00ff41;">
            <div style="color: #00ff41; font-size: 32px; font-weight: 800; margin-bottom: 4px;">{stats['teams']}</div>
            <div style="color: #888; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Teams</div>
        </div>
    </div>
</div>
""", width=280, height=300)

# Player Intelligence Panel (Dynamic - updates on node click)
player_intel_div = Div(text="""
<div style="background: #1a1a1a; padding: 20px; border-radius: 12px; border: 2px dashed #333; min-height: 180px; display: flex; align-items: center; justify-content: center;">
    <div style="text-align: center; color: #666;">
        <p style="margin: 0; font-size: 13px; font-weight: 500;">Click a player node to view</p>
        <p style="margin: 4px 0 0 0; font-size: 11px;">tactical intelligence & passing network</p>
    </div>
</div>
""", width=280, height=220)

# ========== CALLBACKS ==========

filter_callback = CustomJS(args=dict(nodes=nodes_source, edges=edges_source,
                                     team_sel=team_select, cent_slider=centrality_slider,
                                     edge_slider=edge_weight_slider,
                                     search=player_search), code="""
    const node_data = nodes.data;
    const edge_data = edges.data;
    const team = team_sel.value;
    const min_cent = cent_slider.value;
    const min_weight = edge_slider.value;
    const search_term = search.value.toLowerCase();
    
    let visible_nodes = new Set();
    
    for (let i = 0; i < node_data['name'].length; i++) {
        let show = true;
        
        if (team !== "All" && node_data['team'][i] !== team) show = false;
        if (node_data['centrality'][i] < min_cent) show = false;
        if (search_term && !node_data['name'][i].toLowerCase().includes(search_term)) show = false;
        
        if (show) {
            node_data['alpha'][i] = 0.9;
            node_data['current_size'][i] = node_data['base_size'][i];
            visible_nodes.add(node_data['name'][i]);
        } else {
            node_data['alpha'][i] = 0.1;
            node_data['current_size'][i] = Math.max(8, node_data['base_size'][i] * 0.6);
        }
    }
    
    for (let i = 0; i < edge_data['source'].length; i++) {
        if (visible_nodes.has(edge_data['source'][i]) &&
            visible_nodes.has(edge_data['target'][i]) &&
            edge_data['weight'][i] >= min_weight) {
            edge_data['alpha'][i] = edge_data['base_alpha'][i];
        } else {
            edge_data['alpha'][i] = 0.02;
        }
    }
    
    nodes.change.emit();
    edges.change.emit();
""")

team_select.js_on_change('value', filter_callback)
centrality_slider.js_on_change('value', filter_callback)
edge_weight_slider.js_on_change('value', filter_callback)
player_search.js_on_change('value', filter_callback)

# Python callback to fetch player intelligence data server-side
def update_player_intelligence(attrname, old, new):
    """Update player intelligence when a node is selected"""
    if not nodes_source.selected.indices:
        player_intel_div.text = """
        <div style="background: #1a1a1a; padding: 20px; border-radius: 12px; border: 2px dashed #333; min-height: 180px; display: flex; align-items: center; justify-content: center;">
            <div style="text-align: center; color: #666;">
                <p style="margin: 0; font-size: 13px; font-weight: 500;">Click a player node to view</p>
                <p style="margin: 4px 0 0 0; font-size: 11px;">tactical intelligence & passing network</p>
            </div>
        </div>
        """
        return
    
    idx = nodes_source.selected.indices[0]
    player_name = node_data['name'][idx]
    
    intel = get_player_intel(player_name)
    if not intel:
        player_intel_div.text = "<div style='color: #888; padding: 20px;'>Error loading player data</div>"
        return
    
    player = intel['player']
    passed_to = intel['passed_to']
    passed_from = intel['passed_from']
    
    # Build HTML for passed_to list
    passed_to_html = ''.join([
        f"<li style='padding:4px 0; font-size:12px;'><span style='color:#00ff41;'>{p['partner']}</span> ({int(p['volume'])}x)</li>"
        for p in passed_to
    ]) or "<li style='font-size:12px; color:#666;'>No data</li>"
    
    # Build HTML for passed_from list
    passed_from_html = ''.join([
        f"<li style='padding:4px 0; font-size:12px;'><span style='color:#00d4ff;'>{p['partner']}</span> ({int(p['volume'])}x)</li>"
        for p in passed_from
    ]) or "<li style='font-size:12px; color:#666;'>No data</li>"
    
    player_intel_div.text = f"""
    <div style="background: #1a1a1a; padding: 20px; border-radius: 12px; border: 2px solid #00ff41; overflow-y: auto; max-height: 220px;">
        <h3 style="color: #00ff41; margin: 0 0 12px 0; font-size: 16px; font-weight: 700;">{player['name']}</h3>
        <p style="color: #888; margin: 0 0 12px 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
            <strong style="color:#00ff41;">{player['team']}</strong> | Playmaker: {player['centrality']:.4f}
        </p>
        <div style="border-top: 1px solid #333; padding-top: 12px;">
            <div style="margin-bottom: 12px;">
                <p style="color: #00ff41; margin: 0 0 6px 0; font-size: 11px; font-weight: 600;">↓ Passed To (Top 5):</p>
                <ul style="color: #ccc; margin: 0; padding-left: 16px; list-style: none;">{passed_to_html}</ul>
            </div>
            <div>
                <p style="color: #00d4ff; margin: 0 0 6px 0; font-size: 11px; font-weight: 600;">↑ Received From (Top 5):</p>
                <ul style="color: #ccc; margin: 0; padding-left: 16px; list-style: none;">{passed_from_html}</ul>
            </div>
        </div>
    </div>
    """

nodes_source.selected.on_change('indices', update_player_intelligence)

# Click node to highlight its immediate network (graph visualization only)
tap_callback = CustomJS(args=dict(nodes=nodes_source, edges=edges_source), code="""
    const node_data = nodes.data;
    const edge_data = edges.data;
    const selected = nodes.selected.indices;

    // Reset when nothing selected
    if (selected.length === 0) {
        for (let i = 0; i < node_data['name'].length; i++) {
            node_data['alpha'][i] = node_data['base_alpha'][i];
            node_data['current_size'][i] = node_data['base_size'][i];
        }
        for (let i = 0; i < edge_data['source'].length; i++) {
            edge_data['alpha'][i] = edge_data['base_alpha'][i];
        }
        nodes.change.emit();
        edges.change.emit();
        return;
    }

    const idx = selected[0];
    const focus = node_data['name'][idx];
    const neighbors = new Set([focus]);

    for (let i = 0; i < edge_data['source'].length; i++) {
        const s = edge_data['source'][i];
        const t = edge_data['target'][i];
        if (s === focus || t === focus) {
            neighbors.add(s);
            neighbors.add(t);
            edge_data['alpha'][i] = Math.min(0.9, edge_data['base_alpha'][i] + 0.25);
        } else {
            edge_data['alpha'][i] = 0.01;
        }
    }

    for (let i = 0; i < node_data['name'].length; i++) {
        const name = node_data['name'][i];
        if (name === focus) {
            node_data['alpha'][i] = 1.0;
            node_data['current_size'][i] = node_data['base_size'][i] + 8;
        } else if (neighbors.has(name)) {
            node_data['alpha'][i] = 0.95;
            node_data['current_size'][i] = node_data['base_size'][i] + 2;
        } else {
            node_data['alpha'][i] = 0.12;
            node_data['current_size'][i] = Math.max(7, node_data['base_size'][i] * 0.55);
        }
    }

    nodes.change.emit();
    edges.change.emit();
""")
nodes_source.selected.js_on_change('indices', tap_callback)

# Reset callback
reset_callback = CustomJS(args=dict(p=plot), code="""
    p.reset.emit();
""")
reset_btn.js_on_click(reset_callback)

# ========== LAYOUT ==========

# Left Sidebar - Controls (20% width)
controls = column(
    team_select,
    centrality_slider,
    edge_weight_slider,
    player_search,
    reset_btn,
    info_panel,
    player_intel_div,
    sizing_mode="fixed",
    width=240,
    spacing=16,
    styles={'padding': '20px', 'background': '#0f0f0f', 'border-right': '1px solid #1a1a1a', 'overflow-y': 'auto'}
)

# Right Panel - Network + Stats (80% width, split 75/25 internally)
network_canvas = column(
    Div(text="""
    <div style="background:#111;border:1px solid #1f1f1f;border-radius:12px 12px 0 0;
                border-bottom:none;padding:10px 14px;color:#9ca3af;font-size:12px;
                text-transform:uppercase;letter-spacing:0.6px;font-weight:600;">
        Network Canvas
    </div>
    """, sizing_mode="stretch_width", height=38),
    plot,
    sizing_mode="stretch_both",
    spacing=0
)

# Right Stats Column (compact vertical layout)
stats_column = column(
    stats_panel,
    sizing_mode="fixed",
    width=260,
    spacing=0,
    styles={'overflow-y': 'auto', 'padding-right': '8px'}
)

# Combine network + stats in a row (75% / 25% split)
main_canvas_area = row(
    network_canvas,
    stats_column,
    sizing_mode="stretch_both",
    spacing=12
)

# Master Layout: Header + (Sidebar + Canvas)
master_layout = row(
    controls,
    main_canvas_area,
    sizing_mode="stretch_both",
    spacing=12
)

layout = column(
    header,
    master_layout,
    sizing_mode="stretch_both",
    spacing=0
)
layout.name = "app_root"

curdoc().add_root(layout)
curdoc().title = "Euro 2024 Network Explorer"
curdoc().theme = "dark_minimal"
