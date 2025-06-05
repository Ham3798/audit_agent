"""
Database package for audit_agent

This package contains database models and management functionality.
"""

from .models import ScenarioDoc
from .manager import (
    init_db, 
    save_scenario, 
    load_scenario, 
    update_scenario_partial,
    delete_scenario, 
    list_ids, 
    add_runlog_entry
)

__all__ = [
    'ScenarioDoc',
    'init_db',
    'save_scenario',
    'load_scenario', 
    'update_scenario_partial',
    'delete_scenario',
    'list_ids',
    'add_runlog_entry'
] 