import os
import pandas as pd
from statsbombpy import sb

os.makedirs("data", exist_ok=True)

def fetch_quarterfinalist_tournament_data():
    """
    Dynamically identifies Euro 2024 quarter-finalists and extracts all their matches.
    This captures the complete tournament journey of the 8 top-performing teams.
    """
    # Euro 2024 IDs
    COMP_ID = 55
    SEASON_ID = 282
    
    print("📊 Fetching Euro 2024 match list...")
    matches = sb.matches(competition_id=COMP_ID, season_id=SEASON_ID)
    
    # Dynamically identify the 8 teams that reached the Quarter-finals
    qf_matches = matches[matches['competition_stage'] == 'Quarter-finals']
    TARGET_TEAMS = pd.concat([qf_matches['home_team'], qf_matches['away_team']]).unique().tolist()
    
    print(f"🎯 Quarter-finalists identified: {', '.join(sorted(TARGET_TEAMS))}")
    
    # Filter for ALL matches played by these 8 teams throughout the tournament
    # This includes Group Stage, Round of 16, and Quarter-finals
    relevant_matches = matches[
        (matches['home_team'].isin(TARGET_TEAMS)) | 
        (matches['away_team'].isin(TARGET_TEAMS))
    ]
    
    match_ids = relevant_matches['match_id'].tolist()
    print(f"📈 Identified {len(match_ids)} total matches. Starting extraction...\n")
    
    all_passes = []
    
    for i, m_id in enumerate(match_ids):
        print(f"[{i+1}/{len(match_ids)}] Processing Match ID: {m_id}")
        try:
            events = sb.events(match_id=m_id)
            
            # Filter: Successful open-play passes (excluding set pieces)
            passes = events[
                (events['type'] == 'Pass') & 
                (events['pass_outcome'].isna()) &  # Successful only
                (~events['pass_type'].isin(['Throw-in', 'Goal Kick', 'Free Kick', 'Corner']))
            ].copy()
            
            for _, row in passes.iterrows():
                # Only include passes made BY the qualified quarter-finalist teams
                if row['team'] not in TARGET_TEAMS:
                    continue
                    
                loc = row.get('location')
                end_loc = row.get('pass_end_location')
                
                if isinstance(loc, list) and isinstance(end_loc, list):
                    all_passes.append({
                        "team": row['team'],
                        "passer": row['player'],
                        "recipient": row['pass_recipient'],
                        "start_x": loc[0],
                        "start_y": loc[1],
                        "end_x": end_loc[0],
                        "end_y": end_loc[1]
                    })
        except Exception as e:
            print(f"   ⚠️  Error: {str(e)[:60]}")

    df = pd.DataFrame(all_passes)
    print(f"\n✅ Extracted {len(df)} total high-value passes from {len(TARGET_TEAMS)} teams.\n")

    # Aggregate by player pair to find tactical connections
    aggregated = df.groupby(['team', 'passer', 'recipient']).agg(
        start_x=('start_x', 'mean'), 
        start_y=('start_y', 'mean'),
        end_x=('end_x', 'mean'), 
        end_y=('end_y', 'mean'),
        weight=('passer', 'count')  # Edge weight = pass frequency
    ).reset_index()

    output_path = "data/raw_passes.csv"
    aggregated.to_csv(output_path, index=False)
    print(f"💾 Successfully saved quarter-finalist network to {output_path}")
    print(f"   Total player pairs (edges): {len(aggregated)}")
    print(f"   Teams: {', '.join(sorted(aggregated['team'].unique()))}")

if __name__ == "__main__":
    fetch_quarterfinalist_tournament_data()