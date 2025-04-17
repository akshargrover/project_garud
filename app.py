# app.py
from flask import Flask, render_template, request, jsonify
from logistics.cargo_manager import CargoManager
from route_optimizer import EnhancedRouteOptimizer
import json
from datetime import datetime

app = Flask(__name__)
cargo_manager = CargoManager()
route_optimizer = EnhancedRouteOptimizer('models/route_model.pkl')

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/cargo/stats', methods=['GET'])
def cargo_stats():
    """Get cargo statistics"""
    cargo_stats = cargo_manager.get_cargo_stats()
    return jsonify(cargo_stats)

@app.route('/api/shipments/stats', methods=['GET'])
def shipment_stats():
    """Get shipment statistics"""
    stats = cargo_manager.get_shipment_stats()
    return jsonify(stats)

@app.route('/api/shipments/active', methods=['GET'])
def active_shipments():
    """Get all active shipments"""
    shipments = cargo_manager.get_active_shipments()
    # Convert JSON strings to objects
    for shipment in shipments:
        if 'route_data' in shipment and shipment['route_data']:
            shipment['route_data'] = json.loads(shipment['route_data'])
        if 'current_location' in shipment and shipment['current_location']:
            shipment['current_location'] = json.loads(shipment['current_location'])
    
    return jsonify(shipments)

@app.route('/api/shipments/<int:shipment_id>/route', methods=['GET'])
def get_shipment_route(shipment_id):
    """Get optimized route for a shipment"""
    # Get shipment and its cargo
    # (You'd need to add a method to cargo_manager for this)
    
    # For demo purposes, we'll create sample data
    shipment = {
        'id': shipment_id,
        'origin_lat': 34.05,
        'origin_lon': -118.25,
        'dest_lat': 34.22,
        'dest_lon': -118.40,
        'priority': 'urgent'
    }
    
    cargo_list = [
        {'id': 1, 'name': 'Medical Supplies', 'priority': 'critical', 'temperature_min': 2, 'temperature_max': 30},
        {'id': 2, 'name': 'MREs', 'priority': 'standard'}
    ]
    
    # Get optimized route
    route_data = route_optimizer.optimize_for_shipment(shipment, cargo_list)
    
    return jsonify(route_data)

@app.route('/api/shipments/create', methods=['POST'])
def create_shipment():
    """Create a new shipment"""
    data = request.json
    
    shipment_name = data.get('name')
    origin_id = data.get('origin_id')
    destination_id = data.get('destination_id')
    cargo_ids = data.get('cargo_ids', [])
    priority = data.get('priority', 'standard')
    risk_level = data.get('risk_level', 'medium')
    
    # Create shipment
    shipment_id = cargo_manager.create_shipment(
        shipment_name, origin_id, destination_id, cargo_ids,
        priority=priority, risk_level=risk_level
    )
    
    return jsonify({'id': shipment_id, 'status': 'created'})

@app.route('/api/shipments/<int:shipment_id>/update', methods=['POST'])
def update_shipment(shipment_id):
    """Update shipment status"""
    data = request.json
    
    status = data.get('status')
    current_location = data.get('current_location')
    
    cargo_manager.update_shipment_status(shipment_id, status, current_location)
    
    return jsonify({'status': 'updated'})

@app.route('/api/shipments/<int:shipment_id>/environmental', methods=['POST'])
def add_environmental_reading(shipment_id):
    """Add environmental reading for a shipment"""
    data = request.json
    
    temperature = data.get('temperature')
    humidity = data.get('humidity')
    
    cargo_manager.add_environmental_reading(shipment_id, temperature, humidity)
    
    return jsonify({'status': 'added'})

@app.route('/api/shipments/<int:shipment_id>/environmental', methods=['GET'])
def get_environmental_reading(shipment_id):
    """Get latest environmental reading for a shipment"""
    reading = cargo_manager.get_latest_environmental_readings(shipment_id)
    
    return jsonify(reading if reading else {})

if __name__ == '__main__':
    app.run(debug=True)