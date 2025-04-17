# logistics/cargo_manager.py
import json
from datetime import datetime
from models.database import LogisticsDB

class CargoManager:
    def __init__(self, db_file='data/logistics.db'):
        self.db = LogisticsDB(db_file)
    
    def add_cargo(self, name, cargo_type, weight=0, volume=0, priority='standard', 
                 temp_min=None, temp_max=None, humidity_min=None, humidity_max=None):
        """Add a new cargo item to the database"""
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
        INSERT INTO cargo (name, type, weight, volume, priority, 
                          temperature_min, temperature_max, 
                          humidity_min, humidity_max, 
                          created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, cargo_type, weight, volume, priority, 
             temp_min, temp_max, humidity_min, humidity_max, 
             now, now))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def create_shipment(self, name, origin_id, destination_id, cargo_ids, 
                       departure_time=None, priority='standard', risk_level='medium'):
        """Create a new shipment with cargo items"""
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        
        # Create shipment record
        cursor.execute('''
        INSERT INTO shipments (name, origin_id, destination_id, departure_time, 
                              status, priority, risk_level, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, origin_id, destination_id, departure_time, 
             'planning', priority, risk_level, now, now))
        
        shipment_id = cursor.lastrowid
        
        # Add cargo items to shipment
        for cargo_id in cargo_ids:
            cursor.execute('''
            INSERT INTO shipment_items (shipment_id, cargo_id, quantity)
            VALUES (?, ?, ?)
            ''', (shipment_id, cargo_id, 1))
            
            # Update cargo status
            cursor.execute('''
            UPDATE cargo SET status = 'assigned', updated_at = ?
            WHERE id = ?
            ''', (now, cargo_id))
        
        self.db.conn.commit()
        return shipment_id
    
    def update_shipment_status(self, shipment_id, status, current_location=None):
        """Update shipment status and location"""
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        
        if current_location:
            # Convert location to JSON string
            location_json = json.dumps(current_location)
            
            cursor.execute('''
            UPDATE shipments SET status = ?, current_location = ?, updated_at = ?
            WHERE id = ?
            ''', (status, location_json, now, shipment_id))
        else:
            cursor.execute('''
            UPDATE shipments SET status = ?, updated_at = ?
            WHERE id = ?
            ''', (status, now, shipment_id))
        
        # Update cargo status for items in this shipment
        if status == 'delivered':
            cursor.execute('''
            UPDATE cargo SET status = 'delivered', updated_at = ?
            WHERE id IN (
                SELECT cargo_id FROM shipment_items WHERE shipment_id = ?
            )
            ''', (now, shipment_id))
        elif status == 'in_transit':
            cursor.execute('''
            UPDATE cargo SET status = 'in_transit', updated_at = ?
            WHERE id IN (
                SELECT cargo_id FROM shipment_items WHERE shipment_id = ?
            )
            ''', (now, shipment_id))
        
        self.db.conn.commit()
        
    def get_shipment_stats(self):
        """Get shipment statistics by status"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT status, COUNT(*) as count
        FROM shipments
        GROUP BY status
        ''')
        
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_cargo_stats(self):
        """Get cargo statistics by status"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT status, COUNT(*) as count
        FROM cargo
        GROUP BY status
        ''')
        
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_active_shipments(self):
        """Get all active shipments (planning or in_transit)"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT s.*, 
               o.name as origin_name, o.latitude as origin_lat, o.longitude as origin_lon,
               d.name as dest_name, d.latitude as dest_lat, d.longitude as dest_lon
        FROM shipments s
        JOIN locations o ON s.origin_id = o.id
        JOIN locations d ON s.destination_id = d.id
        WHERE s.status IN ('planning', 'in_transit')
        ''')
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def add_environmental_reading(self, shipment_id, temperature, humidity):
        """Record environmental conditions for a shipment"""
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
        INSERT INTO environmental_readings (shipment_id, temperature, humidity, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (shipment_id, temperature, humidity, now))
        
        self.db.conn.commit()
        
    def get_latest_environmental_readings(self, shipment_id):
        """Get latest environmental readings for a shipment"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT * FROM environmental_readings
        WHERE shipment_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        ''', (shipment_id,))
        
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
        return None