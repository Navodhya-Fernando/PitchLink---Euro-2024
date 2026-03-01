import os
import pandas as pd
from py2neo import Graph
from dotenv import load_dotenv

load_dotenv()
graph = Graph(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")))

def build_tournament_graph():
    print("Clearing database for Euro 2024 Quarter-Finalist data...")
    graph.run("MATCH (n) DETACH DELETE n")

    df = pd.read_csv("data/raw_passes.csv")
    passes = df.to_dict("records")

    print(f"📊 Building graph for {len(passes)} aggregated passing lanes...")

    # Optimized Cypher: Creates Teams, Players, and Weighted Pass Relationships
    cypher_query = """
    UNWIND $passes AS pass
    MERGE (t:Team {name: pass.team})
    MERGE (p1:Player {name: pass.passer})
    MERGE (p2:Player {name: pass.recipient})
    
    // Link players to their national teams
    MERGE (p1)-[:PLAYS_FOR]->(t)
    MERGE (p2)-[:PLAYS_FOR]->(t)
    
    // Create a single weighted edge for the entire tournament
    CREATE (p1)-[r:PASSED_TO]->(p2)
    SET r.weight = pass.weight,
        r.start_x = pass.start_x,
        r.start_y = pass.start_y,
        r.end_x = pass.end_x,
        r.end_y = pass.end_y
    """
    graph.run(cypher_query, passes=passes)
    
    # Get counts
    node_count = graph.evaluate('MATCH (n) RETURN count(n)')
    player_count = graph.evaluate('MATCH (p:Player) RETURN count(p)')
    team_count = graph.evaluate('MATCH (t:Team) RETURN count(t)')
    edge_count = graph.evaluate('MATCH ()-[r:PASSED_TO]->() RETURN count(r)')
    
    print("\n✅ Graph Build Complete!")
    print(f"   Players: {player_count}")
    print(f"   Teams: {team_count}")
    print(f"   Passing connections (edges): {edge_count}")
    print(f"   Total nodes: {node_count}")

if __name__ == "__main__":
    build_tournament_graph()