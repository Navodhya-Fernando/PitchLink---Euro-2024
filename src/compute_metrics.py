import os
import networkx as nx
import pandas as pd
from py2neo import Graph
from dotenv import load_dotenv

load_dotenv()
graph = Graph(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")))

def classify_player_role(name, betweenness, in_degree, position_x, position_y):
    """Classify player role based on metrics and position"""
    # Defensive zone: x < 40
    # Middle zone: 40 <= x <= 80
    # Attacking zone: x > 80
    
    if position_x is None:
        return "Unknown"
    
    if position_x < 40:
        if betweenness > 0.03:
            return "Deep Playmaker"
        elif in_degree > 30:
            return "Center Back"
        else:
            return "Fullback"
    elif position_x <= 80:
        if betweenness > 0.02:
            return "Box-to-Box"
        elif in_degree > 25:
            return "Midfielder"
        else:
            return "Defensive Mid"
    else:  # Attacking zone
        if betweenness > 0.015:
            return "Creative Forward"
        elif in_degree > 20:
            return "Striker"
        else:
            return "Winger"

def compute_comparative_metrics():
    # Dynamically read all teams from the CSV data
    df = pd.read_csv("data/raw_passes.csv")
    teams = sorted(df['team'].unique().tolist())
    
    print(f"📊 Found {len(teams)} teams in dataset")
    print(f"   Teams: {', '.join(teams)}\n")
    
    for team in teams:
        print(f"🔍 Computing comprehensive metrics for {team}...")
        
        # Get player positions
        team_passes = df[df['team'] == team]
        player_positions = {}
        for _, row in team_passes.iterrows():
            if row['passer'] not in player_positions:
                player_positions[row['passer']] = (row['start_x'], row['start_y'])
            if row['recipient'] not in player_positions:
                player_positions[row['recipient']] = (row['start_x'], row['start_y'])
        
        # Pull only this team's passing network
        query = """
        MATCH (p1:Player)-[r:PASSED_TO]->(p2:Player)
        MATCH (p1)-[:PLAYS_FOR]->(t:Team {name: $team_name})
        RETURN p1.name AS source, p2.name AS target, r.weight AS weight
        """
        results = graph.run(query, team_name=team).data()
        
        G = nx.DiGraph()
        for row in results:
            G.add_edge(row['source'], row['target'], weight=row['weight'])
        
        # 1. Betweenness Centrality
        betweenness = nx.betweenness_centrality(G, normalized=True, weight='weight')
        
        # 2. PageRank (influence-based)
        pagerank = nx.pagerank(G, weight='weight')
        
        # 3. Eigenvector Centrality
        try:
            eigenvector = nx.eigenvector_centrality(G, max_iter=100, weight='weight')
        except:
            eigenvector = {node: 0 for node in G.nodes()}
        
        # 4. Clustering Coefficient (community detection)
        G_undirected = G.to_undirected()
        clustering = nx.clustering(G_undirected, weight='weight')
        
        # 5. In-degree & Out-degree
        in_degree = dict(G.in_degree(weight='weight'))
        out_degree = dict(G.out_degree(weight='weight'))
        
        # 6. Progressive Pass Detection
        progressive_passes = {}
        for node in G.nodes():
            progressive_passes[node] = 0
        
        for _, row in team_passes.iterrows():
            # Progressive if moves >15 yards toward goal (increasing start_x)
            if row['end_x'] - row['start_x'] > 15:
                if row['passer'] in progressive_passes:
                    progressive_passes[row['passer']] += row['weight']
        
        # 7. Zone Analysis (Def=0-40, Mid=40-80, Att=80-120)
        zones = {}
        for player, (x, y) in player_positions.items():
            if x < 40:
                zones[player] = "Defensive"
            elif x <= 80:
                zones[player] = "Midfield"
            else:
                zones[player] = "Attacking"
        
        # 8. Calculate Network Stats
        avg_path_length = nx.average_shortest_path_length(G.to_undirected()) if nx.is_connected(G.to_undirected()) else 0
        density = nx.density(G)
        
        # Write back to Neo4j
        metrics_data = []
        for node in G.nodes():
            pos = player_positions.get(node, (60, 40))
            role = classify_player_role(node, betweenness.get(node, 0), 
                                       in_degree.get(node, 0), pos[0], pos[1])
            
            metrics_data.append({
                "name": node,
                "in_degree": float(in_degree.get(node, 0)),
                "out_degree": float(out_degree.get(node, 0)),
                "betweenness": float(round(betweenness.get(node, 0), 4)),
                "pagerank": float(round(pagerank.get(node, 0), 4)),
                "eigenvector": float(round(eigenvector.get(node, 0), 4)),
                "clustering": float(round(clustering.get(node, 0), 4)),
                "progressive_passes": float(round(progressive_passes.get(node, 0), 1)),
                "zone": zones.get(node, "Unknown"),
                "role": role,
                "network_density": float(round(density, 4)),
                "avg_path_length": float(round(avg_path_length, 2))
            })

        update_query = """
        UNWIND $metrics AS m
        MATCH (p:Player {name: m.name})
        SET p.in_degree = m.in_degree,
            p.out_degree = m.out_degree,
            p.betweenness = m.betweenness,
            p.pagerank = m.pagerank,
            p.eigenvector = m.eigenvector,
            p.clustering = m.clustering,
            p.progressive_passes = m.progressive_passes,
            p.zone = m.zone,
            p.role = m.role,
            p.network_density = m.network_density,
            p.avg_path_length = m.avg_path_length
        """
        graph.run(update_query, metrics=metrics_data)
        
        print(f"  ✓ {len(metrics_data)} players analyzed")
        print(f"  • Network Density: {density:.4f}")
        print(f"  • Avg Path Length: {avg_path_length:.2f}")

    print("\n✅ All Comparative Metrics Computed & Stored")

if __name__ == "__main__":
    compute_comparative_metrics()