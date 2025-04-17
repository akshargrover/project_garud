# models/database.py
import sqlite3
import os
from datetime import datetime

class LogisticsDB:
    def __init__(self, db_file='data/logistics.db'):
        self.db_file = db_file
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.conn = sqlite3.connect(db_file)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Cargo items table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cargo (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            weight REAL,
            volume REAL,
            priority TEXT,
            status TEXT DEFAULT 'pending',
            temperature_min REAL,
            temperature_max REAL,
            humidity_min REAL,
            humidity_max REAL,
            created_at DATETIME,
            updated_at DATETIME
        )
        ''')
        
        # Shipments table - groups of cargo
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            origin_id INTEGER,
            destination_id INTEGER,
            departure_time DATETIME,
            arrival_time DATETIME,
            status TEXT DEFAULT 'planning',
            route_data TEXT, -- JSON string of route coordinates
            current_location TEXT, -- JSON coordinates
            priority TEXT DEFAULT 'standard',
            risk_level TEXT DEFAULT 'medium',
            created_at DATETIME,
            updated_at DATETIME
        )
        ''')
        
        # Shipment items - links cargo to shipments
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shipment_items (
            id INTEGER PRIMARY KEY,
            shipment_id INTEGER,
            cargo_id INTEGER,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (shipment_id) REFERENCES shipments (id),
            FOREIGN KEY (cargo_id) REFERENCES cargo (id)
        )
        ''')
        
        # Locations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            latitude REAL,
            longitude REAL,
            description TEXT
        )
        ''')
        
        # Environmental readings
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS environmental_readings (
            id INTEGER PRIMARY KEY,
            shipment_id INTEGER,
            temperature REAL,
            humidity REAL,
            timestamp DATETIME,
            FOREIGN KEY (shipment_id) REFERENCES shipments (id)
        )
        ''')
        
        self.conn.commit()