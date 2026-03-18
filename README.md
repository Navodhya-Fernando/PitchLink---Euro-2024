# PitchLink Euro 2024 — Tactical Network Engine

*Elite Command Center for football tactical analysis featuring Pitch Overlay, Edge Intelligence, Community Clusters, and Scouting AI.*

![Platform](https://img.shields.io/badge/Platform-Web-4A90E2)
![Backend](https://img.shields.io/badge/Backend-Python-3776AB)
![Data Source](https://img.shields.io/badge/Data-Event%20Data-FF6B6B)
![UI](https://img.shields.io/badge/UI-Bokeh%20JS-F7DF1E)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Overview

**PitchLink Euro 2024** is a specialized tactical engine that tracks passing networks, identifies tactical micro-structures (clusters), and dynamically scouts key playmakers using graph theory. Built for analysts and scouts to dissect match and tournament data using interactive network visualizations.

**🌐 Live Demo:** https://pitchlink-euro-2024-production.up.railway.app/app

---

## 🧠 Core Features

* 🕸️ **Network Intelligence** — Models passing behavior via PageRank and Betweenness Centrality
* 🧩 **Tactical Units** — Uses the Louvain algorithm to automatically detect player communities and positional clusters
* 🕵️ **Scouting AI** — Generates real-time text briefings highlighting progressive passing hubs and focal points
* 🔍 **Advanced Filtering** — Isolate by team, scale by centrality, or filter out low-value connections
* 📈 **Leaderboard Roster** — Interactive datatables dynamically updating based on on-pitch selections
* 🎨 **Elite Dark UI** — Custom 100vh Bokeh dark mode with neon green/cyan terminal aesthetics

---

## 📁 Project Structure

```bash
tactical-engine/
│
├── app/
│   ├── main.py               # Core Bokeh application & graph logic
│   └── templates/
│       └── index.html        # Custom Jinja2 dark-mode wrapper
├── data/
│   └── raw_passes.csv        # Passing event dataset
├── src/                      
│   ├── build_graph.py        # Graph processing utilities
│   ├── compute_metrics.py    # Math/algorithmic models
│   └── fetch_statsbomb.py    # Data ingestion scripts
├── Dockerfile                # Production server specs
├── requirements.txt          # Python dependencies
├── LICENSE
└── README.md
```

---

## ⚙️ Local Development Setup

### 1️⃣ Install Dependencies

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Data Availability

`data/raw_passes.csv` is already included in this repository, so you can run the app immediately.

Optional: regenerate the dataset from StatsBomb source data:

```bash
pip install statsbombpy
python src/fetch_statsbomb.py
```

### 3️⃣ Start the Application Server

Run the Bokeh directory app locally:

```bash
bokeh serve app --show
```

### 4️⃣ Access the App

Your browser will automatically open, or you can navigate to:
```
http://localhost:5006/app
```

---

## 🔬 Tactical Metrics Explained

### Centrality (PageRank)
Calculates a player's importance not just by how many passes they receive, but by the quality of the players passing to them. Identifies the true focal point of a team's transition system.

### Louvain Communities
Groups players who interact with each other significantly more than with the rest of the team, successfully uncovering tactical "pods" (e.g., a left-sided triangle of LB-LW-LCM).

### Progressive Passes
Highlights vertical line-breaking actions, helping to distinguish between safe lateral recycling and high-value infiltration passing.

---

## 🎨 UI Features

* **Glow Selection** — Clicking a node dims non-associated players and brightens exact passing routes
* **Auto-Search** — Real-time JS-based autocomplete that immediately centers the pitch on the queried player
* **Granular Edges** — Pass lines scale in opacity and thickness based on the volume and progression-value
* **Crosshair Tracking** — Tactical crosshair cursors and hover-tooltips for precise spatial analysis

---

## 🚀 Deployment

This application is containerized and optimized for cloud platforms.

### Deploying to Railway / Render (Docker)

1. Connect your GitHub repository to [Railway.app](https://railway.app/).
2. Railway will automatically detect the `Dockerfile`.
3. The `Dockerfile` natively binds to the `$PORT` variable for seamless web port mapping.
4. Set memory allocation. (Graph generation is memory-intensive; 1GB+ recommended).
5. Open your generated domain to view the application!

---

## 📊 App Data Flow

```text
Data Ingestion (CSV) 
        ↓
NetworkX Directed/Undirected Graphs Created
        ↓
Louvain & PageRank Algorithms Computed
        ↓
ColumnDataSources synced to Bokeh Interface
        ↓
Jinja2 Custom HTML Matrix applies Dark CSS
        ↓
JS Callbacks trigger real-time UI/Scouting changes
```

---

## 🐛 Troubleshooting

**Blank White Screen on Load**
- Ensure you are running `bokeh serve app` (the directory) rather than `bokeh serve app/main.py`. The directory setup is required to utilize `index.html`.

**Internal Server Error (500) during Deployment**
- Ensure `scipy` is in your `requirements.txt` (required under the hood by NetworkX PageRank).
- Ensure the platform is injecting a valid `$PORT` environment variable that the Docker container binds to.

---

## 📝 Technical Stack

| Layer | Technology |
|-------|-----------|
| Backend / Logic | Python 3.10+, NetworkX, SciPy, Pandas |
| Visual Framework | Bokeh |
| Community Detection | Python-Louvain |
| Infrastructure | Docker, Bash |
| UI/UX | HTML5, CSS3, Bokeh CustomJS |

---

## 🪪 License

MIT License — Copyright © 2026 Navodhya Fernando

See [LICENSE](LICENSE) for full details.

---

## 👨‍💻 Developer

**Navodhya Fernando**  
Data & Web System Engineer @DreamShift INC  
Data Science Undergraduate at National Innovation Centre (NIBM), Colombo 05, Sri Lanka  
In partnership with Coventry University
