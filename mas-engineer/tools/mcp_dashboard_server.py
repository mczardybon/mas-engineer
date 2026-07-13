#!/usr/bin/env python3
"""MCP Dashboard Server - Provides realtime dashboard data to Goose UI
========================================================================
This module exposes dashboard data via MCP for the HTML dashboard.

Usage: Imported by MCP server or called directly for data.
"""
import json
import os
from pathlib import Path


class DashboardMCP:
    """MCP handler for dashboard data requests"""
    
    def __init__(self, workspace=None):
        self.workspace = workspace or os.environ.get('MAS_WORKSPACE', '.')
        self.dashboard_dir = os.path.join(self.workspace, '.mas', 'dashboards')
    
    def get_data(self) -> dict:
        """Get current dashboard data from cache/file"""
        data_path = os.path.join(self.dashboard_dir, 'data.json')
        
        if os.path.exists(data_path):
            try:
                with open(data_path) as f:
                    return json.load(f)
            except:
                pass
        
        # Fallback: generate fresh data
        return self._generate_fresh_data()
    
    def _generate_fresh_data(self) -> dict:
        """Generate fresh dashboard data"""
        # Import and call the dashboard generator
        try:
            from dev_dashboard_data import generate_data
            return generate_data(self.workspace)
        except ImportError:
            return {
                "error": "Dashboard generator not available",
                "timestamp": None,
                "workspace": self.workspace
            }
    
    def handle_request(self, method: str, params: dict) -> dict:
        """Handle MCP request"""
        if method == 'ui/dashboard/data' or method == 'dashboard:data':
            return self.get_data()
        elif method == 'ui/dashboard/refresh':
            return self._generate_fresh_data()
        elif method == 'ui/dashboard/subscribe':
            # Return subscription confirmation
            return {
                "subscribed": True,
                "events": params.get('events', [])
            }
        else:
            return {"error": f"Unknown method: {method}"}
    
    def notify_update(self, event: str, data: dict = None):
        """Send notification about dashboard update"""
        return {
            "method": event,
            "params": data or self.get_data()
        }


def get_dashboard_data(workspace: str = None) -> dict:
    """Main entry point for getting dashboard data"""
    handler = DashboardMCP(workspace)
    return handler.get_data()


if __name__ == '__main__':
    # CLI usage
    import sys
    ws = sys.argv[1] if len(sys.argv) > 1 else '.'
    data = get_dashboard_data(ws)
    print(json.dumps(data, indent=2))
