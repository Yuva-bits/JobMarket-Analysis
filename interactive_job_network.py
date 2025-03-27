import json
import sys
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
from collections import defaultdict
import plotly.express as px
import os
from plotly.subplots import make_subplots
import math

def load_network_data(file_path="job_network.json"):
    """Load network data from JSON file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: Could not find {file_path}")
        print("Please run view_job_relationships.py first and export the network data.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        sys.exit(1)

def create_graph(network_data):
    """Create a NetworkX graph from the network data"""
    G = nx.Graph()
    
    # Add nodes with attributes
    for node in network_data.get("nodes", []):
        G.add_node(
            node["id"],
            name=node.get("name", ""),
            node_type=node.get("type", ""),
            category=node.get("category", ""),
            entity_type=node.get("entity_type", ""),
            company=node.get("company", "")
        )
    
    # Add edges with attributes
    for link in network_data.get("links", []):
        G.add_edge(
            link["source"],
            link["target"],
            type=link.get("type", "")
        )
    
    return G

def get_node_color_mapping():
    """Create color mappings for different node types and categories"""
    # Define a modern color palette with more distinct colors
    node_type_colors = {
        "job": "#6495ED",      # Cornflower Blue
        "skill": "#66CDAA",    # Medium Aquamarine
        "entity": "#FF7F50"    # Coral
    }
    
    # Skill category colors - using a more harmonious palette
    category_colors = {
        "programming_language": "#4169E1",  # Royal Blue
        "web_development": "#20B2AA",       # Light Sea Green
        "data_science": "#9370DB",          # Medium Purple
        "database": "#3CB371",              # Medium Sea Green
        "cloud_devops": "#4682B4",          # Steel Blue
        "ai_llm": "#8A2BE2",                # Blue Violet
        "project_management": "#DAA520",    # Goldenrod
        "soft_skill": "#7B68EE",            # Medium Slate Blue
        "other": "#A9A9A9"                  # Dark Gray
    }
    
    # Entity type colors
    entity_type_colors = {
        "WORKS_AT": "#FF6347",  # Tomato
        "LOCATED_IN": "#FF8C00"  # Dark Orange
    }
    
    return node_type_colors, category_colors, entity_type_colors

def create_interactive_network(G, output_file="interactive_job_network.html", title="Interactive Job Network Analysis"):
    """Create an interactive visualization of the job network using Plotly"""
    # Get color mappings
    node_type_colors, category_colors, entity_type_colors = get_node_color_mapping()
    
    # Create layout - force-directed layout for better visualization
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    
    # Prepare node data
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    node_symbols = []
    
    # Define node type symbols
    symbols = {
        "job": "circle",
        "skill": "diamond",
        "entity": "square"
    }
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Node attributes
        node_type = G.nodes[node].get("node_type", "")
        node_name = G.nodes[node].get("name", "")
        category = G.nodes[node].get("category", "")
        company = G.nodes[node].get("company", "")
        
        # Add node color based on type and category
        if node_type == "job":
            node_color.append(node_type_colors.get("job"))
            node_size.append(20)  # Jobs are larger
        elif node_type == "skill":
            node_color.append(category_colors.get(category, category_colors["other"]))
            # Size based on degree centrality
            degree = G.degree(node)
            node_size.append(10 + (degree * 2))
        elif node_type == "entity":
            entity_type = G.nodes[node].get("entity_type", "")
            node_color.append(entity_type_colors.get(entity_type, entity_type_colors.get("WORKS_AT")))
            node_size.append(15)
        else:
            node_color.append("#CCCCCC")  # Default gray
            node_size.append(10)  # Default size
        
        # Add node symbol based on type
        node_symbols.append(symbols.get(node_type, "circle"))
        
        # Create node text
        if node_type == "job":
            hover_text = f"<b>Job:</b> {node_name}<br><b>Company:</b> {company or 'N/A'}<br><b>Connections:</b> {G.degree(node)}"
        elif node_type == "skill":
            hover_text = f"<b>Skill:</b> {node_name}<br><b>Category:</b> {category or 'N/A'}<br><b>Used in:</b> {G.degree(node)} jobs"
        elif node_type == "entity":
            entity_type = G.nodes[node].get("entity_type", "N/A")
            hover_text = f"<b>Entity:</b> {node_name}<br><b>Type:</b> {entity_type}<br><b>Connections:</b> {G.degree(node)}"
        else:
            hover_text = f"{node_name} (Unknown type)"
        
        node_text.append(hover_text)
    
    # Prepare edge data
    edge_x = []
    edge_y = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        
        # Add line trace points
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Create edge trace
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color="#CCCCCC"),
        mode="lines",
        hoverinfo="none",
        showlegend=False
    )
    
    # Create node trace
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        hoverinfo="text",
        marker=dict(
            color=node_color,
            size=node_size,
            symbol=node_symbols,
            line=dict(width=1, color="#FFFFFF")
        ),
        text=node_text,
        hovertemplate="%{text}<extra></extra>"
    )
    
    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace])
    
    # Add legend for node types and categories
    legend_traces = []
    
    # Add node type legend
    for node_type, color in node_type_colors.items():
        legend_trace = go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=color, symbol=symbols.get(node_type, "circle")),
            name=f"{node_type.capitalize()}",
            hoverinfo="none",
            showlegend=True
        )
        legend_traces.append(legend_trace)
    
    # Add skill category legend
    for category, color in category_colors.items():
        if category == "other":
            continue  # Skip 'other' category in legend
        
        # Format category name for display
        category_name = category.replace("_", " ").title()
        
        legend_trace = go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=color, symbol="diamond"),
            name=f"{category_name} Skill",
            hoverinfo="none",
            showlegend=True
        )
        legend_traces.append(legend_trace)
    
    # Add legend traces to figure
    for trace in legend_traces:
        fig.add_trace(trace)
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20)
        ),
        showlegend=True,
        legend=dict(
            title=dict(text="Node Types"),
            font=dict(size=10),
            itemsizing="constant",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.05
        ),
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        annotations=[
            dict(
                text="Job Market Skills Network",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#FFFFFF",
        height=800,
        width=1200
    )
    
    # Create the visualization
    fig.write_html(
        output_file,
        include_plotlyjs="cdn",
        full_html=True,
        config={
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
            "displaylogo": False,
            "responsive": True
        }
    )
    
    print(f"Interactive network visualization saved to {output_file}")
    return fig

def create_skill_distribution_chart(G, output_file="skill_distribution.html"):
    """Create a visualization of skill distribution across job postings"""
    # Count skill occurrences
    skill_counts = {}
    skill_categories = {}
    
    for node in G.nodes():
        if G.nodes[node].get("node_type") == "skill":
            skill_name = G.nodes[node].get("name", "")
            category = G.nodes[node].get("category", "other")
            degree = G.degree(node)  # Number of connections
            
            skill_counts[skill_name] = degree
            skill_categories[skill_name] = category
    
    # Convert to DataFrame for easier visualization
    if not skill_counts:
        print("No skills found in the network.")
        return
    
    # Create DataFrame
    df = pd.DataFrame({
        "Skill": list(skill_counts.keys()),
        "Count": list(skill_counts.values()),
        "Category": [skill_categories[skill] for skill in skill_counts.keys()]
    })
    
    # Sort by count
    df = df.sort_values("Count", ascending=False).head(30)  # Show top 30 skills
    
    # Get color mapping
    _, category_colors, _ = get_node_color_mapping()
    
    # Convert category colors to list for plotly
    color_map = {cat: color for cat, color in category_colors.items()}
    
    # Create bar chart
    fig = px.bar(
        df,
        x="Skill",
        y="Count",
        color="Category",
        color_discrete_map=color_map,
        title="Top 30 Skills by Frequency in Job Postings",
        labels={"Count": "Number of Job Postings", "Skill": "Skill Name", "Category": "Skill Category"},
        height=600
    )
    
    # Update layout
    fig.update_layout(
        xaxis=dict(tickangle=-45),
        plot_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=50, b=100)
    )
    
    # Save the chart
    fig.write_html(
        output_file,
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": False, "responsive": True}
    )
    
    print(f"Skill distribution chart saved to {output_file}")
    return fig

def create_category_distribution_chart(G, output_file="category_distribution.html"):
    """Create a visualization of skill categories distribution"""
    # Count skill categories
    category_counts = defaultdict(int)
    
    for node in G.nodes():
        if G.nodes[node].get("node_type") == "skill":
            category = G.nodes[node].get("category", "other")
            category_counts[category] += 1
    
    # Convert to DataFrame
    if not category_counts:
        print("No skill categories found in the network.")
        return
    
    # Create DataFrame
    df = pd.DataFrame({
        "Category": [cat.replace("_", " ").title() for cat in category_counts.keys()],
        "Count": list(category_counts.values())
    })
    
    # Sort by count
    df = df.sort_values("Count", ascending=False)
    
    # Get color mapping
    _, category_colors, _ = get_node_color_mapping()
    
    # Convert category colors to list for plotly
    color_map = {cat.replace("_", " ").title(): color for cat, color in category_colors.items()}
    
    # Create pie chart
    fig = px.pie(
        df,
        values="Count",
        names="Category",
        color="Category",
        color_discrete_map=color_map,
        title="Distribution of Skill Categories",
        height=500
    )
    
    # Update layout
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    # Update traces
    fig.update_traces(textposition="inside", textinfo="percent+label")
    
    # Save the chart
    fig.write_html(
        output_file,
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": False, "responsive": True}
    )
    
    print(f"Category distribution chart saved to {output_file}")
    return fig

def analyze_network(G):
    """Analyze the network and print statistics"""
    print("\n=== Network Analysis ===")
    
    # Basic network statistics
    print(f"Number of nodes: {G.number_of_nodes()}")
    print(f"Number of edges: {G.number_of_edges()}")
    
    # Node type counts
    node_types = defaultdict(int)
    for node in G.nodes():
        node_type = G.nodes[node].get("node_type", "unknown")
        node_types[node_type] += 1
    
    print("\nNode types:")
    for node_type, count in node_types.items():
        print(f"  - {node_type}: {count}")
    
    # Skill categories
    if node_types["skill"] > 0:
        skill_categories = defaultdict(int)
        for node in G.nodes():
            if G.nodes[node].get("node_type") == "skill":
                category = G.nodes[node].get("category", "unknown")
                skill_categories[category] += 1
        
        print("\nSkill categories:")
        for category, count in skill_categories.items():
            print(f"  - {category}: {count}")
    
    # Most connected nodes (degree centrality)
    degree_centrality = nx.degree_centrality(G)
    top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print("\nMost connected nodes (Degree Centrality):")
    for node, centrality in top_nodes:
        node_name = G.nodes[node].get("name", node)
        node_type = G.nodes[node].get("node_type", "unknown")
        print(f"  - {node_name} ({node_type}): {centrality:.4f}")
    
    # Betweenness centrality for key skills that bridge job domains
    if len(G.nodes()) <= 1000:  # Only compute if graph is not too large
        betweenness_centrality = nx.betweenness_centrality(G, k=min(100, G.number_of_nodes()))
        skill_betweenness = [(node, cent) for node, cent in betweenness_centrality.items() 
                          if G.nodes[node].get("node_type") == "skill"]
        top_betweenness = sorted(skill_betweenness, key=lambda x: x[1], reverse=True)[:10]
        
        print("\nKey bridge skills (Betweenness Centrality):")
        for node, centrality in top_betweenness:
            node_name = G.nodes[node].get("name", node)
            category = G.nodes[node].get("category", "unknown")
            print(f"  - {node_name} ({category}): {centrality:.4f}")
    
    # Network density
    density = nx.density(G)
    print(f"\nNetwork density: {density:.4f}")
    
    # Average clustering coefficient
    avg_clustering = nx.average_clustering(G)
    print(f"Average clustering coefficient: {avg_clustering:.4f}")

def create_dashboard(G, output_folder="job_market_dashboard"):
    """Create a comprehensive dashboard with multiple visualizations"""
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Create the network visualization
    network_path = os.path.join(output_folder, "job_network.html")
    network_fig = create_interactive_network(G, output_file=network_path)
    
    # Create skill distribution chart
    skill_dist_path = os.path.join(output_folder, "skill_distribution.html")
    skill_dist_fig = create_skill_distribution_chart(G, output_file=skill_dist_path)
    
    # Create category distribution chart
    cat_dist_path = os.path.join(output_folder, "category_distribution.html")
    cat_dist_fig = create_category_distribution_chart(G, output_file=cat_dist_path)
    
    # Create index.html to combine all visualizations
    index_path = os.path.join(output_folder, "index.html")
    
    with open(index_path, "w") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Market Skills Analysis Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #4682B4;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .viz-container {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            padding: 15px;
        }
        .viz-title {
            font-size: 18px;
            margin-bottom: 10px;
            color: #4682B4;
        }
        .viz-description {
            margin-bottom: 15px;
            color: #666;
        }
        .iframe-container {
            position: relative;
            overflow: hidden;
            width: 100%;
        }
        iframe {
            border: none;
            width: 100%;
        }
        .network-viz iframe {
            height: 800px;
        }
        .chart-viz iframe {
            height: 600px;
        }
        .two-col {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        .col {
            flex: 1;
            min-width: 300px;
        }
        @media (max-width: 768px) {
            .two-col {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Job Market Skills Analysis Dashboard</h1>
        <p>Interactive visualization of job postings and related skills</p>
    </div>
    
    <div class="container">
        <div class="viz-container network-viz">
            <h2 class="viz-title">Job-Skill Network Analysis</h2>
            <div class="viz-description">
                <p>Interactive network graph showing relationships between jobs and skills. Jobs are represented as circles, and skills as diamonds.
                The size of each node indicates its importance in the network. Hover over nodes to see detailed information.</p>
                <p><strong>Interaction tips:</strong> Zoom with mouse wheel, pan by clicking and dragging, hover for details.</p>
            </div>
            <div class="iframe-container">
                <iframe src="job_network.html"></iframe>
            </div>
        </div>
        
        <div class="two-col">
            <div class="col">
                <div class="viz-container chart-viz">
                    <h2 class="viz-title">Top Skills Distribution</h2>
                    <div class="viz-description">
                        <p>Bar chart showing the frequency of top skills across job postings, color-coded by skill category.</p>
                    </div>
                    <div class="iframe-container">
                        <iframe src="skill_distribution.html"></iframe>
                    </div>
                </div>
            </div>
            
            <div class="col">
                <div class="viz-container chart-viz">
                    <h2 class="viz-title">Skill Categories Distribution</h2>
                    <div class="viz-description">
                        <p>Pie chart showing the distribution of skill categories in the job market.</p>
                    </div>
                    <div class="iframe-container">
                        <iframe src="category_distribution.html"></iframe>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>""")
    
    print(f"\nDashboard created in {output_folder}/")
    print(f"Open {index_path} in a web browser to view the dashboard.")

def main():
    """Main function"""
    # Get input file path
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "job_network.json"
    
    # Load network data
    print(f"Loading network data from {input_file}...")
    network_data = load_network_data(input_file)
    
    # Create network graph
    G = create_graph(network_data)
    
    # Analyze network
    analyze_network(G)
    
    # Create dashboard with all visualizations
    create_dashboard(G)

if __name__ == "__main__":
    main() 