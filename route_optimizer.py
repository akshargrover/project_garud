import osmnx as ox
import folium
import networkx as nx
import pandas as pd
from flask import Flask, render_template
import branca.colormap as cm
from datetime import datetime
import plotly.graph_objects as go
import numpy as np

class RouteOptimizerBackend:
    def __init__(self):
        self.graph = None
        self.model = None
        self.feature_columns = None
        
    def load_model(self, model_path):
        """Load trained ML model"""
        import pickle
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
    def load_graph(self, location):
        """Load road network graph"""
        self.graph = ox.graph_from_place(location, network_type='drive')
        
    def predict_route(self, start_point, end_point, time_of_day, day_of_week, 
                      mission_priority='standard', risk_tolerance='medium'):
        """Generate optimal route based on model predictions and mission parameters"""
        # Convert coordinates to graph nodes
        start_node = ox.distance.nearest_nodes(self.graph, start_point[1], start_point[0])
        end_node = ox.distance.nearest_nodes(self.graph, end_point[1], end_point[0])
        
        # Create temporary graph with ML-predicted weights
        G_temp = self.graph.copy()
        
        # Apply weights based on ML predictions
        for u, v, k, data in G_temp.edges(data=True, keys=True):
            # Extract features
            features = self.extract_edge_features(G_temp, u, v, k, time_of_day, day_of_week)
            
            # Adjust for mission priority and risk tolerance
            risk_factor = 1.0
            if risk_tolerance == 'low':
                risk_factor = 1.5  # Prefer safer routes even if longer
            elif risk_tolerance == 'high':
                risk_factor = 0.7  # Willing to take more risks for faster routes
                
            # Predict travel time
            pred_time = self.model.predict([features])[0] * risk_factor
            
            # Set edge weight
            G_temp[u][v][k]['weight'] = pred_time
        
        # Find shortest path
        try:
            route = nx.shortest_path(G_temp, start_node, end_node, weight='weight')
            route_edges = list(zip(route[:-1], route[1:]))
            
            # Extract route coordinates for mapping
            route_coords = []
            for u, v in route_edges:
                # Get coordinates for this edge
                coords = G_temp.edges[u, v, 0].get('geometry', None)
                if coords:
                    # If we have LineString geometry
                    for coord in coords.coords:
                        route_coords.append((coord[1], coord[0]))  # Folium expects (lat, lon)
                else:
                    # If we don't have geometry, use node coordinates
                    route_coords.append((G_temp.nodes[u]['y'], G_temp.nodes[u]['x']))
                    route_coords.append((G_temp.nodes[v]['y'], G_temp.nodes[v]['x']))
            
            return route_coords, route
        except:
            return None, None
    # route_optimizer.py

class EnhancedRouteOptimizer:
    def __init__(self, model_path=None):
        # Initialize your base route optimizer
        self.optimizer = RouteOptimizerBackend()
        if model_path:
            self.optimizer.load_model(model_path)
    
    def optimize_for_shipment(self, shipment, cargo_list, current_time=None):
        """
        Optimize route considering cargo constraints
        
        Parameters:
        shipment (dict): Shipment information
        cargo_list (list): List of cargo items in the shipment
        current_time (datetime): Current time for optimization
        
        Returns:
        dict: Optimized route information
        """
        # Extract basic route information
        origin = (shipment['origin_lat'], shipment['origin_lon'])
        destination = (shipment['dest_lat'], shipment['dest_lon'])
        
        # Set current time if not provided
        if not current_time:
            current_time = datetime.now()
        
        time_of_day = current_time.hour
        day_of_week = current_time.weekday()
        
        # Determine constraints based on cargo
        constraints = self._get_cargo_constraints(cargo_list)
        
        # Adjust risk tolerance based on cargo priority
        risk_tolerance = 'medium'  # default
        if any(cargo['priority'] == 'critical' for cargo in cargo_list):
            risk_tolerance = 'low'  # safer routes for critical cargo
        elif all(cargo['priority'] == 'low' for cargo in cargo_list):
            risk_tolerance = 'high'  # can take more risks for low priority
            
        # Determine mission priority
        mission_priority = shipment.get('priority', 'standard')
        
        # Get optimized route
        route_coords, route_nodes = self.optimizer.predict_route(
            origin, destination, time_of_day, day_of_week,
            mission_priority=mission_priority,
            risk_tolerance=risk_tolerance
        )
        
        # Add cargo-specific considerations
        route_metrics = self._calculate_cargo_metrics(route_nodes, constraints)
        
        return {
            'route': route_coords,
            'metrics': route_metrics,
            'estimated_duration': route_metrics.get('total_time', 0),
            'risk_level': self._calculate_risk_level(route_metrics)
        }
    
    def _get_cargo_constraints(self, cargo_list):
        """Extract constraints from cargo items"""
        constraints = {
            'temp_sensitive': False,
            'max_temp': None,
            'min_temp': None,
            'humidity_sensitive': False,
            'max_humidity': None,
            'min_humidity': None,
            'total_weight': 0,
            'total_volume': 0,
            'has_dangerous_goods': False
        }
        
        for cargo in cargo_list:
            # Track temperature requirements
            if cargo.get('temperature_min') is not None or cargo.get('temperature_max') is not None:
                constraints['temp_sensitive'] = True
                
                if cargo.get('temperature_min') is not None:
                    if constraints['min_temp'] is None or cargo['temperature_min'] > constraints['min_temp']:
                        constraints['min_temp'] = cargo['temperature_min']
                
                if cargo.get('temperature_max') is not None:
                    if constraints['max_temp'] is None or cargo['temperature_max'] < constraints['max_temp']:
                        constraints['max_temp'] = cargo['temperature_max']
            
            # Track humidity requirements
            if cargo.get('humidity_min') is not None or cargo.get('humidity_max') is not None:
                constraints['humidity_sensitive'] = True
                
                if cargo.get('humidity_min') is not None:
                    if constraints['min_humidity'] is None or cargo['humidity_min'] > constraints['min_humidity']:
                        constraints['min_humidity'] = cargo['humidity_min']
                
                if cargo.get('humidity_max') is not None:
                    if constraints['max_humidity'] is None or cargo['humidity_max'] < constraints['max_humidity']:
                        constraints['max_humidity'] = cargo['humidity_max']
            
            # Track weight and volume
            constraints['total_weight'] += cargo.get('weight', 0)
            constraints['total_volume'] += cargo.get('volume', 0)
            
            # Check for dangerous goods
            if cargo.get('type') in ['ammunition', 'explosive', 'fuel', 'chemical']:
                constraints['has_dangerous_goods'] = True
        
        return constraints
    
    def _calculate_cargo_metrics(self, route_nodes, constraints):
        """Calculate route metrics considering cargo constraints"""
        # Basic metrics
        metrics = {
            'total_distance': 0,
            'total_time': 0,
            'risk_score': 0,
            'environmental_risk': 0,
            'safe_zones': 0,
            'danger_zones': 0
        }
        
        # Add your route metrics calculation logic here
        # This would typically consider the specific edges in your graph
        # and factor in cargo constraints
        
        # Example pseudocode:
        # for each segment in route_nodes:
        #    segment_metrics = calculate_segment_metrics(segment)
        #    apply_cargo_constraints(segment_metrics, constraints)
        #    update overall metrics
        
        # Mock calculation for demonstration
        metrics['total_distance'] = 100  # km
        metrics['total_time'] = 120  # minutes
        
        # Increase risk score for sensitive cargo
        if constraints['temp_sensitive'] or constraints['humidity_sensitive']:
            metrics['environmental_risk'] = 30
        
        # Increase risk for dangerous goods
        if constraints['has_dangerous_goods']:
            metrics['risk_score'] += 50
            metrics['danger_zones'] = 2
        
        return metrics
    
    def _calculate_risk_level(self, metrics):
        """Determine overall risk level based on metrics"""
        total_risk = metrics['risk_score'] + metrics['environmental_risk']
        
        if total_risk < 30:
            return 'low'
        elif total_risk < 70:
            return 'medium'
        else:
            return 'high'

risk_factors = {
    'low': 1.5,    # Safer routes
    'medium': 1.0,  # Balanced
    'high': 0.7     # Faster but riskier
}

# 1. Initialize with ML model
optimizer = EnhancedRouteOptimizer('models/route_model.pkl')

# 2. Input: Shipment details and cargo list
shipment = {
    'origin_lat': 34.05,
    'origin_lon': -118.25,
    'dest_lat': 34.22,
    'dest_lon': -118.40,
    'priority': 'urgent'
}

cargo_list = [
    {'name': 'Medical Supplies', 'priority': 'critical', 'temperature_min': 2}
]