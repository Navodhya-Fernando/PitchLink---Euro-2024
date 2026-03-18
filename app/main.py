"""
PITCHLINK EURO 2024 - Elite Command Center
Features: Pitch Overlay, Edge Intelligence, Community Clusters, Scouting AI
"""
from bokeh.io import curdoc
from bokeh.layouts import column, row, Spacer
from bokeh.models import (Select, Slider, TextInput, AutocompleteInput, Button, Div, CustomJS, 
                          HoverTool, ColumnDataSource, DataTable, TableColumn, NumberFormatter)
from bokeh.plotting import figure
import os
import networkx as nx
from networkx.algorithms import community
import pandas as pd
import numpy as np

# ========== 1. DATA LOADING & COMMUNITY DETECTION ==========
def load_network_data():
    """Load network with Louvain community detection for tactical units"""
    print("📊 Loading network with community detection...")
    
    # Load dataset
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_passes.csv")
    df = pd.read_csv(csv_path)
    
    # Build NetworkX Multi-DiGraph (for accurate PageRank) to compute metrics
    edges_df = df.groupby(['passer', 'recipient', 'team']).agg({
        'weight': 'sum',
        'start_x': 'mean',
        'start_y': 'mean'
    }).reset_index()
    
    # Calculate average node positions overall
    node_positions = pd.concat([
        df[['passer', 'team', 'start_x', 'start_y']].rename(columns={'passer': 'player'}),
        df[['recipient', 'team', 'end_x', 'end_y']].rename(columns={'recipient': 'player', 'end_x': 'start_x', 'end_y': 'start_y'})
    ]).groupby(['player', 'team']).mean().reset_index()
    
    # We build an undirected graph for Louvain, and directed graph for Centrality metrics
    G_directed = nx.DiGraph()
    G_undirected = nx.Graph()
    
    players = {}
    
    for _, row in node_positions.iterrows():
        p = row['player']
        players[p] = {
            'team': row['team'], 
            'progressive_passes': 0,
            'x': row['start_x'],
            'y': row['start_y']
        }
    
    for _, row in edges_df.iterrows():
        passer = row['passer']
        recipient = row['recipient']
        weight = row['weight']
        
        # Ensure they exist (edge case if grouped out)
        if passer not in players: players[passer] = {'team': row['team'], 'progressive_passes': 0, 'x': row['start_x'], 'y': row['start_y']}
        if recipient not in players: players[recipient] = {'team': row['team'], 'progressive_passes': 0, 'x': 60, 'y': 40}
            
        G_directed.add_edge(passer, recipient, weight=weight)
        
        # For undirected, just sum weights
        if G_undirected.has_edge(passer, recipient):
            G_undirected[passer][recipient]['weight'] += weight
        else:
            G_undirected.add_edge(passer, recipient, weight=weight)
    
    # Add progressive passes logic implicitly based on data (simulated for now since coordinates aren't easy to filter here directly, we'll assign random or basic pass volume)
    for p in players:
        players[p]['progressive_passes'] = int(G_directed.out_degree(p, weight='weight') * 0.2) # rough proxy
    
    print(f"   Network built: {len(players)} players, {len(G_undirected.edges)} undirected edges")
    
    # Compute Centrality Metrics
    pageranks = nx.pagerank(G_directed, weight='weight')
    betweenness = nx.betweenness_centrality(G_undirected, weight='weight', normalized=True)
    
    # Detect Communities per Team (Louvain)
    print("   Detecting tactical units...")
    cluster_map = {}
    cluster_counter = 0
    for team in df['team'].unique():
        # Get team subgraph
        team_players = [p for p, data in players.items() if data['team'] == team]
        team_subgraph = G_undirected.subgraph(team_players)
        
        if len(team_subgraph.nodes) > 0:
            clusters = community.louvain_communities(team_subgraph, weight='weight', seed=42)
            for i, group in enumerate(clusters):
                for name in group:
                    cluster_map[name] = cluster_counter + i
            cluster_counter += len(clusters)
            
    # Compile Node Data
    G = G_undirected 
    
    # Convert Statsbomb/Opta coords (0-120x, 0-80y) to Bokeh pitch coords (-1.0 to 1.0)
    # Pitch rect was drawn: x=0,y=0, w=2.2, h=1.6 => x from -1.1 to 1.1, y from -0.8 to 0.8
    def scale_x(x): return (x / 120.0) * 2.2 - 1.1
    def scale_y(y): return (y / 80.0) * 1.6 - 0.8
    
    node_data = {
        'name': [], 'x': [], 'y': [], 'current_size': [], 'base_size': [],
        'color': [], 'alpha': [], 'team': [], 'cluster': [], 'centrality': [],
        'role': [], 'progressive_passes': [], 'pagerank': [], 'cluster_color': [], 'role_color': []
    }
    
    cluster_palette = ['#00ff41', '#00d4ff', '#ff1744', '#ffeb3b', '#e91e63', '#9c27b0']
    role_colors = {
        "Deep Playmaker": "#ff1744", "Center Back": "#00d4ff", "Fullback": "#00ff41",
        "Box-to-Box": "#ffeb3b", "Midfielder": "#e91e63", "Defensive Mid": "#9c27b0",
        "Creative Forward": "#ff9800", "Striker": "#f44336", "Winger": "#4caf50", "Unknown": "#888888"
    }
    
    for name in G.nodes():
        node_attr = players[name]
        
        node_data['name'].append(name)
        # Flip Y to match standard pitch orientation if necessary, but direct mapping works:
        node_data['x'].append(scale_x(node_attr['x']))
        node_data['y'].append(scale_y(node_attr['y']))
        
        cluster_id = cluster_map.get(name, 0)
        c_color = cluster_palette[cluster_id % len(cluster_palette)]
        
        # Determine pseudo-role based on metrics
        pr = pageranks.get(name, 0)
        bw = betweenness.get(name, 0)
        
        role = "Midfielder"
        if pr > np.percentile(list(pageranks.values()), 80): role = "Deep Playmaker"
        elif bw > np.percentile(list(betweenness.values()), 80): role = "Creative Forward"
        
        r_color = role_colors.get(role, "#888888")
        
        node_data['cluster_color'].append(c_color)
        node_data['role_color'].append(r_color)
        node_data['color'].append(c_color) # Default to cluster color initially
        node_data['alpha'].append(1.0)  # Make nodes brighter
        
        # Sizing based on pagerank for more visible insightful scaling
        size = 18 + (pr * 600)
        if size < 18: size = 18 + (bw * 300)
        
        node_data['current_size'].append(size)
        node_data['base_size'].append(size)
        node_data['team'].append(node_attr['team'])
        node_data['cluster'].append(f"Unit {cluster_id + 1}")
        node_data['centrality'].append(bw)
        node_data['role'].append(role)
        node_data['progressive_passes'].append(node_attr['progressive_passes'])
        node_data['pagerank'].append(pr)

    # Prepare edge data with descriptions and width for glow effect
    edge_data = {
        'x0': [], 'y0': [], 'x1': [], 'y1': [], 'weight': [], 'alpha': [], 
        'base_alpha': [], 'desc': [], 'source': [], 'target': [], 'width': [], 'base_width': []
    }
    
    for u, v, d in G.edges(data=True):
        edge_data['x0'].append(scale_x(players[u]['x']))
        edge_data['y0'].append(scale_y(players[u]['y']))
        edge_data['x1'].append(scale_x(players[v]['x']))
        edge_data['y1'].append(scale_y(players[v]['y']))
        weight = d['weight']
        edge_data['weight'].append(weight)
        
        # Feature 4: Edge Intelligence - Detailed pass description
        edge_desc = f"{u} ↔ {v}: {int(weight)} passes"
        edge_data['desc'].append(edge_desc)
        edge_data['source'].append(u)
        edge_data['target'].append(v)
        
        alpha = min(0.3 + weight * 0.02, 0.8)  # Noticeably brighter edges
        edge_data['alpha'].append(alpha)
        edge_data['base_alpha'].append(alpha)
        
        # Width for glow effect
        base_width = max(1.5, min(5.0, weight * 0.08))
        edge_data['width'].append(base_width)
        edge_data['base_width'].append(base_width)

    print(f"✅ Network loaded: {len(node_data['name'])} nodes, {len(edge_data['source'])} edges")
    
    return ColumnDataSource(node_data), ColumnDataSource(edge_data)

nodes_source, edges_source = load_network_data()


# ========== 2. TACTICAL INSIGHTS ENGINE ==========
def generate_scouting_report(team_name, source):
    """Generates an automated tactical summary based on data source"""
    df = pd.DataFrame(source.data)
    if team_name != "All":
        df = df[df['team'] == team_name]
    
    if len(df) == 0:
        return "Select a team to generate scouting insights."
        
    top_player = df.loc[df['centrality'].idxmax()]
    name = top_player['name']
    
    if team_name == "All":
        team_str = "The tournament"
    else:
        team_str = f"{team_name}'s system"
        
    return f"<b>Tactical Note:</b> {team_str} revolves around <b>{name}</b>, who acts as the primary hub for passing transitions."

# ========== VISUALIZATION ==========

# ========== 3. THE PROFESSIONAL CANVAS ==========
plot = figure(
    sizing_mode="stretch_both", 
    background_fill_color="#121212", 
    border_fill_color="#121212",
    x_range=(-1.2, 1.2), 
    y_range=(-1.2, 1.2),
    tools="pan,wheel_zoom,tap,reset,save",
    active_scroll="wheel_zoom",
    outline_line_color="#333333"
)
plot.axis.visible = False
plot.grid.visible = False

# Feature 1: Pitch Background Overlay - Modern glowing style
plot.rect(x=0, y=0, width=2.2, height=1.6, fill_alpha=0.03, fill_color="#00ff41", line_color="#00ff41", line_alpha=0.2, line_width=1)
plot.line(x=[0, 0], y=[-0.8, 0.8], line_color="#00ff41", line_alpha=0.2, line_width=1)
plot.circle(x=0, y=0, radius=0.2, fill_alpha=0, line_color="#00ff41", line_alpha=0.2, line_width=1)
plot.circle(x=0, y=0, radius=0.02, fill_alpha=0.2, fill_color="#00ff41", line_color=None)
# Penalty Areas
plot.rect(x=-0.92, y=0, width=0.36, height=0.8, fill_alpha=0, line_color="#00ff41", line_alpha=0.2, line_width=1)
plot.rect(x=0.92, y=0, width=0.36, height=0.8, fill_alpha=0, line_color="#00ff41", line_alpha=0.2, line_width=1)
# Goal Areas
plot.rect(x=-1.04, y=0, width=0.12, height=0.36, fill_alpha=0, line_color="#00ff41", line_alpha=0.2, line_width=1)
plot.rect(x=1.04, y=0, width=0.12, height=0.36, fill_alpha=0, line_color="#00ff41", line_alpha=0.2, line_width=1)

# Renderers (with dynamic width for glow effect)
edge_r = plot.segment(x0='x0', y0='y0', x1='x1', y1='y1', 
                      line_color="#333", line_alpha='alpha', line_width='width',
                      source=edges_source)
node_r = plot.circle(x='x', y='y', size='current_size', 
                     color='color', alpha='alpha', 
                     line_color="#121212", line_width=2.5,
                     source=nodes_source)

# Unified Hover Tooltip (Prevents Overlap)
hover = HoverTool(renderers=[node_r], tooltips="""
    <div style="background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(10px); border: 1px solid #00ff41; padding: 15px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,255,65,0.2);">
        <div style="margin-bottom: 5px;">
            <span style="color: #00ff41; font-weight: 800; font-size: 16px; letter-spacing: 0.5px;">@name</span>
            <span style="float: right; color: #fff; background: #333; padding: 2px 6px; border-radius: 4px; font-size: 11px;">@team</span>
        </div>
        <div style="color: #a0aec0; font-size: 13px; margin-bottom: 8px; border-bottom: 1px solid #334155; padding-bottom: 8px;">
            <strong style="color: #cbd5e1;">Role:</strong> @role<br>
            <strong style="color: #cbd5e1;">Unit:</strong> @cluster
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px;">
            <div><span style="color: #94a3b8;">Prog. Passes</span><br><span style="color: #38bdf8; font-weight: bold; font-size: 14px;">@progressive_passes</span></div>
            <div><span style="color: #94a3b8;">PageRank</span><br><span style="color: #fbbf24; font-weight: bold; font-size: 14px;">@pagerank{0.000}</span></div>
        </div>
    </div>
""")
plot.add_tools(hover)

# ========== 4. THE COMMAND CENTER LAYOUT ==========
# Fix Header Overlap: Use margin-left to push text away from the icon
header = Div(text="""
<div style="background: linear-gradient(90deg, #111 0%, #0a0a0a 100%); padding: 15px 30px; border-bottom: 2px solid #00ff41; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 15px rgba(0,255,65,0.15);">
    <div style="display: flex; align-items: center;">
        <div style="margin-right: 20px; background: #00ff41; color: #000; padding: 5px 12px; border-radius: 4px; font-weight: 900; font-size: 13px; letter-spacing: 1px; animation: pulse 2s infinite;">LIVE</div>
        <h1 style="color: #fff; margin: 0; font-size: 26px; font-family: 'Inter', 'Segoe UI', sans-serif; font-weight: 800; letter-spacing: 2px;">PITCHLINK <span style="color:#00ff41;">EURO 2024</span></h1>
    </div>
    <div style="color: #666; font-size: 14px; font-family: monospace;">TACTICAL ANALYSIS ENGINE v2.0</div>
    <style>@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }</style>
</div>
""", sizing_mode="stretch_width")

# Generate initial scouting report
scouting_div = Div(text=generate_scouting_report("Spain", nodes_source), 
                   styles={"color": "#e2e8f0", "font-size": "14px", "padding": "20px", "background": "rgba(255,255,255,0.03)", "border-left": "4px solid #00ff41", "border-radius": "8px", "line-height": "1.6", "box-shadow": "inset 0 0 20px rgba(0,0,0,0.5)"})

# Feature 1 & 3: Tactical Leaderboard Table
player_list = nodes_source.data
leaderboard_data = {
    'name': player_list['name'][:20],  # Top 20 for display
    'cluster': player_list['cluster'][:20],
    'team': player_list['team'][:20]
}
leaderboard_source = ColumnDataSource(leaderboard_data)

columns = [
    TableColumn(field="name", title="Player"),
    TableColumn(field="team", title="Team"),
    TableColumn(field="cluster", title="Unit")
]
leaderboard = DataTable(
    source=leaderboard_source, 
    columns=columns, 
    width=290, 
    height=250, 
    background="#111",
    index_position=None
)

# Build sidebar
teams = sorted(list(set(nodes_source.data['team'])))
team_select = Select(
    title="Isolate Team", 
    options=["All"] + teams,
    value="All", 
    width=270
)

all_players = sorted(list(set(nodes_source.data['name'])))
player_search = AutocompleteInput(
    title="Search Player", 
    completions=all_players,
    value="",
    placeholder="e.g., Toni Kroos",
    width=270
)

pass_weight_slider = Slider(
    title="Min Centrality (scaled)", 
    start=0, end=100, value=0, 
    width=270
)

color_by_select = Select(
    title="Color Nodes By", 
    options=["Tactical Unit", "Player Role"],
    value="Tactical Unit", 
    width=270
)

# ========== INTERACTION CALLBACKS ==========

# Click-to-Highlight Callback (Fades Non-Connected Nodes/Edges)
tap_js = CustomJS(args=dict(nodes=nodes_source, edges=edges_source, div=scouting_div), code="""
    const n_data = nodes.data;
    const e_data = edges.data;
    const selected = nodes.selected.indices;

    if (selected.length === 0) {
        // Reset View
        for (let i = 0; i < n_data['alpha'].length; i++) n_data['alpha'][i] = 0.9;
        for (let i = 0; i < e_data['alpha'].length; i++) {
            e_data['alpha'][i] = e_data['base_alpha'][i];
            e_data['width'][i] = e_data['base_width'][i]; // Reset width
        }
    } else {
        const idx = selected[0];
        const focus = n_data['name'][idx];
        const team = n_data['team'][idx];
        const role = n_data['role'][idx];
        const unit = n_data['cluster'][idx];
        const prog = n_data['progressive_passes'][idx];
        let partners = new Set([focus]);

        // Highlight active edges with GLOW effect
        for (let i = 0; i < e_data['source'].length; i++) {
            if (e_data['source'][i] === focus || e_data['target'][i] === focus) {
                e_data['alpha'][i] = 1.0; // Brighten
                e_data['width'][i] = e_data['base_width'][i] + 3; // GLOW via width increase
                partners.add(e_data['source'][i]);
                partners.add(e_data['target'][i]);
            } else {
                e_data['alpha'][i] = 0.02; // Fade inactive lines
                e_data['width'][i] = e_data['base_width'][i];
            }
        }

        // Fade non-partner nodes
        for (let i = 0; i < n_data['name'].length; i++) {
            n_data['alpha'][i] = partners.has(n_data['name'][i]) ? 1.0 : 0.15;
        }
        
        // Update Scouting Report with Player Insight
        div.text = `
            <div style="font-family: sans-serif;">
                <h4 style="color: #00ff41; margin: 0 0 5px 0; font-size: 16px;">Player Insight</h4>
                <b style="color: white; font-size: 18px;">${focus}</b> <span style="color: #888;">(${team})</span><br><br>
                <b style="color: #cbd5e1;">Role:</b> ${role}<br>
                <b style="color: #cbd5e1;">Tactical Unit:</b> ${unit}<br>
                <b style="color: #cbd5e1;">Prog. Passes:</b> <span style="color: #38bdf8;">${prog}</span><br><br>
                <span style="color: #94a3b8; font-size: 13px;">Click empty pitch area to clear selection.</span>
            </div>
        `;
    }
    nodes.change.emit();
    edges.change.emit();
""")

# Filter Callback (Team + Centrality)
filter_js = CustomJS(args=dict(nodes=nodes_source, edges=edges_source, team_sel=team_select, 
                               cent_slider=pass_weight_slider, color_sel=color_by_select,
                               leaderboard=leaderboard_source), code="""
    const n_data = nodes.data;
    const e_data = edges.data;
    const l_data = leaderboard.data;
    const team = team_sel.value;
    const min_cent = cent_slider.value / 1000.0; // Convert slider to centrality scale
    const color_mode = color_sel.value;

    let visible_nodes = new Set();
    
    // Arrays for updating leaderboard
    let new_l_names = [];
    let new_l_teams = [];
    let new_l_clusters = [];

    for (let i = 0; i < n_data['name'].length; i++) {
        let show = true;
        if (team !== "All" && n_data['team'][i] !== team) show = false;
        if (n_data['centrality'][i] < min_cent) show = false;
        
        n_data['alpha'][i] = show ? 0.9 : 0.0;
        n_data['current_size'][i] = show ? n_data['base_size'][i] : 0;
        
        if (color_mode === "Player Role") {
            n_data['color'][i] = n_data['role_color'][i];
        } else {
            n_data['color'][i] = n_data['cluster_color'][i];
        }
        
        if (show) {
            visible_nodes.add(n_data['name'][i]);
            new_l_names.push(n_data['name'][i]);
            new_l_teams.push(n_data['team'][i]);
            new_l_clusters.push(n_data['cluster'][i]);
        }
    }
    
    // Update Leaderboard Data
    l_data['name'] = new_l_names;
    l_data['team'] = new_l_teams;
    l_data['cluster'] = new_l_clusters;
    leaderboard.change.emit();
    
    // Filter edges based on visible nodes
    for (let i = 0; i < e_data['source'].length; i++) {
        if (visible_nodes.has(e_data['source'][i]) && visible_nodes.has(e_data['target'][i])) {
            e_data['alpha'][i] = e_data['base_alpha'][i];
        } else {
            e_data['alpha'][i] = 0.0;
        }
    }
    
    nodes.change.emit();
    edges.change.emit();
""")

# Report callback
report_js = CustomJS(args=dict(source=nodes_source, team_sel=team_select, div=scouting_div), code="""
    const data = source.data;
    const team = team_sel.value;
    
    let top_centrality = -1;
    let top_player = "";
    
    for (let i=0; i < data['name'].length; i++) {
        if (team === "All" || data['team'][i] === team) {
            if (data['centrality'][i] > top_centrality) {
                top_centrality = data['centrality'][i];
                top_player = data['name'][i];
            }
        }
    }
    
    if (top_player !== "") {
        let team_str = team === "All" ? "The tournament" : team + "'s system";
        div.text = '<b>Tactical Note:</b> ' + team_str + ' revolves around <b>' + top_player + '</b>, who acts as the primary hub for passing transitions.';
    } else {
        div.text = 'Select a team to generate scouting insights.';
    }
""")

# Search Callback
search_js = CustomJS(args=dict(nodes=nodes_source, search=player_search), code="""
    const data = nodes.data;
    const query = search.value;
    
    if (query !== "") {
        const idx = data['name'].indexOf(query);
        if (idx !== -1) {
            nodes.selected.indices = [idx];
        }
    }
""")

# Attach callbacks
team_select.js_on_change('value', filter_js, report_js)
pass_weight_slider.js_on_change('value', filter_js)
color_by_select.js_on_change('value', filter_js)
player_search.js_on_change('value', search_js)
nodes_source.selected.js_on_change('indices', tap_js)

sidebar = column(
    team_select,
    player_search,
    pass_weight_slider,
    color_by_select,
    Spacer(height=10),
    Div(text="<h3 style='color:#00ff41; font-size:14px; margin-bottom:5px; margin-top:10px; letter-spacing: 1px; border-bottom: 1px solid #333; padding-bottom: 5px; text-transform: uppercase;'>Network Intelligence</h3>"),
    scouting_div,
    Spacer(height=10),
    Div(text="<h3 style='color:#00ff41; font-size:14px; margin-bottom:5px; margin-top:10px; letter-spacing: 1px; border-bottom: 1px solid #333; padding-bottom: 5px; text-transform: uppercase;'>Unit Roster</h3>"),
    leaderboard,
    sizing_mode="fixed", 
    width=340,
    spacing=15,
    styles={"background": "linear-gradient(180deg, #121212 0%, #0a0a0a 100%)", "border-right": "1px solid rgba(255,255,255,0.05)", "overflow-y": "auto", "padding": "25px", "box-shadow": "5px 0 20px rgba(0,0,0,0.8)"}
)

# Final layout
layout = column(
    header, 
    row(sidebar, plot, sizing_mode="stretch_both"), 
    sizing_mode="stretch_both",
    min_height=800,
    min_width=1000
)
layout.name = "app_root"

curdoc().add_root(layout)
curdoc().title = "PITCHLINK EURO 2024"
curdoc().theme = "dark_minimal"

from jinja2 import Template
template_string = """
{% extends base %}
{% block postamble %}
  <style>
    html, body {
      width: 100%;
      height: 100vh;
      margin: 0;
      padding: 0;
      background-color: #121212;
      overflow: hidden;
    }
  </style>
{% endblock %}
"""
curdoc().template = Template(template_string)
