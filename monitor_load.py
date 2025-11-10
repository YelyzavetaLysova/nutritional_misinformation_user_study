"""
Simple monitoring script to track concurrent participants.
Run this alongside your survey to monitor capacity.
"""

import time
import logging
from datetime import datetime
from app.db import get_quality_metrics

def monitor_participants():
    """Monitor participant load and performance."""
    while True:
        try:
            metrics = get_quality_metrics()
            active_sessions = len([p for p in participants.values() if not p.completed])
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Active: {active_sessions} | Total: {metrics['total_participants']} | Completed: {metrics['completed_participants']}")
            
            # Warn if approaching limits
            if active_sessions > 30:
                print("⚠️  WARNING: High concurrent load detected!")
            elif active_sessions > 50:
                print("🚨 CRITICAL: Very high load - consider scaling!")
                
        except Exception as e:
            print(f"Monitoring error: {e}")
        
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    print("Starting participant monitoring...")
    monitor_participants()
