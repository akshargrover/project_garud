import osmnx as ox

# Specify the Indian city
city_name = "Delhi, India"

# Load the road network for the city
G = ox.graph_from_place(city_name, network_type="drive")

# Convert the graph edges to a GeoDataFrame
edges = ox.graph_to_gdfs(G, nodes=False)

# Save the road network data to a CSV file
edges.to_csv("delhi_road_network.csv")

print("Road network data for Delhi has been saved to 'delhi_road_network.csv'")