import os
import pandas as pd
from statsbombpy import sb

os.makedirs("data", exist_ok=True)

def fetch_semi_finalist_data():
    # Euro 2024 IDs
    COMP_ID = 55
    SEASON_ID = 282
    
    # Expanded: All Quarterfinalists + Semi-finalists (8 teams for richer network)
    TARGET_TEAMS = [
        'Spain', 'England', 'France', 'Netherlands',  # Semi-finalists
        'Germany', 'Portugal', 'Switzerland', 'Turkey'  # Additional quarterfinalists
    ]
    
    print(f"Fetching all Euro 2024 matches for: {', '.join(TARGET_TEAMS)}...")
    matches = sb.matches(competition_id=COMP_ID, season_id=SEASON_ID)
    
    # Filter for matches where at least one target team played
    target_matches = matches[
        (matches['home_team'].isin(TARGET_TEAMS)) | 
        (matches['away_team'].isin(TARGET_TEAMS))
    ]
    
    match_ids = target_matches['match_id'].tolist()
    print(f"Identified {len(match_ids)} relevant matches. Starting extraction...")
    
    all_passes = []
    
    for i, m_id in enumerate(match_ids):
        print(f"[{i+1}/{len(match_ids)}] Processing Match ID: {m_id}")
        try:
            events = sb.events(match_id=m_id)
            
            # Filter: Successful open-play passes
            passes = events[
                (events['type'] == 'Pass') & 
                (events['pass_outcome'].isna()) & # Successful only
                (~events['pass_type'].isin(['Throw-in', 'Goal Kick', 'Free Kick', 'Corner']))
            ].copy()
            
            for _, row in passes.iterrows():
                # We only care about passes made BY our target teams
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
            print(f"Error skipping match {m_id}: {e}")

    df = pd.DataFrame(all_passes)
    print(f"\nExtracted {len(df)} total semi-finalist passes.")

    # Aggregate by player pair to find tactical connections
    aggregated = df.groupby(['team', 'passer', 'recipient']).agg(
        start_x=('start_x', 'mean'), start_y=('start_y', 'mean'),
        end_x=('end_x', 'mean'), end_y=('end_y', 'mean'),
        weight=('passer', 'count') # This is the edge weight
    ).reset_index()

    output_path = "data/raw_passes.csv"
    aggregated.to_csv(output_path, index=False)
    print(f"Successfully saved aggregated network to {output_path}")

if __name__ == "__main__":
    fetch_semi_finalist_data()