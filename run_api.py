#!/usr/bin/env python3
"""
API server entry point for the YOLOv11 object detection and tracking application.
This script starts the Flask-based API server for remote control of the detection system.
"""

import sys
import os
import threading

# Add the src directory to the Python path so imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main function to run the API server."""
    from src.api_server import app
    print("Starting YOLOv11-Speed API server...")
    print("Access the web interface at: http://localhost:8000/")
    print("API endpoints available at: http://localhost:8000/api/")
    
    # Start the API server
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)

if __name__ == "__main__":
    main()
