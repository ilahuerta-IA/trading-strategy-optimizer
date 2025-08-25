"""
Strategy registration module.
This module provides a centralized way to register and load strategy classes.
"""

from typing import Dict, Type, List
import importlib
from pathlib import Path

# Strategy registry dictionary
STRATEGY_REGISTRY: Dict[str, Dict[str, str]] = {}

def register_strategy(name: str, module_path: str, class_name: str):
    """
    Register a strategy in the global registry.
    
    Args:
        name: The string identifier for the strategy (e.g., 'CorrelatedSMACross')
        module_path: The module path (e.g., 'strategies.correlated_sma_cross')
        class_name: The class name (e.g., 'CorrelatedSMACrossStrategy')
    """
    STRATEGY_REGISTRY[name] = {
        'module': module_path,
        'class': class_name
    }

def get_strategy_class(strategy_name: str):
    """
    Dynamically load and return a strategy class by name.
    
    Args:
        strategy_name: The registered strategy name
        
    Returns:
        The strategy class object
        
    Raises:
        ValueError: If strategy is not registered
        ImportError: If module cannot be imported
        AttributeError: If class is not found in module
    """
    if strategy_name not in STRATEGY_REGISTRY:
        available_strategies = list(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Strategy '{strategy_name}' not found. Available strategies: {available_strategies}")
    
    strategy_info = STRATEGY_REGISTRY[strategy_name]
    module_path = strategy_info['module']
    class_name = strategy_info['class']
    
    try:
        # Import the module
        strategy_module = importlib.import_module(module_path)
        
        # Get the class from the module
        strategy_class = getattr(strategy_module, class_name)
        
        return strategy_class
        
    except ImportError as e:
        raise ImportError(f"Could not import module '{module_path}' for strategy '{strategy_name}': {e}")
    except AttributeError as e:
        raise AttributeError(f"Class '{class_name}' not found in module '{module_path}' for strategy '{strategy_name}': {e}")

def list_available_strategies() -> List[str]:
    """Return a list of all registered strategy names."""
    return list(STRATEGY_REGISTRY.keys())

def get_strategy_info(strategy_name: str) -> Dict[str, str]:
    """Get module and class information for a strategy."""
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(f"Strategy '{strategy_name}' not registered")
    return STRATEGY_REGISTRY[strategy_name].copy()

# Register all available strategies
register_strategy('CorrelatedSMACross', 'strategies.correlated_sma_cross', 'CorrelatedSMACrossStrategy')
register_strategy('MACrossOver', 'strategies.ma_cci_crossover', 'MACrossOver')
register_strategy('BBandPearsonDivergence', 'strategies.bband_pearson_divergence', 'BBandPearsonDivergence')
register_strategy('SunriseSimple', 'strategies.sunrise_simple', 'SunriseSimple')

# Import strategy classes for direct access
try:
    from .sunrise_simple import SunriseSimple
except ImportError:
    pass

# Export the main functions
__all__ = [
    'register_strategy',
    'get_strategy_class', 
    'list_available_strategies',
    'get_strategy_info',
    'STRATEGY_REGISTRY',
    'SunriseSimple'  # Export the strategy class directly
]