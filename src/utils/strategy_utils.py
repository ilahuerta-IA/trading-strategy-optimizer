# utils/strategy_utils.py
from typing import Dict, List, Any, Type
import importlib
import inspect
from strategies import strategy_registry

def get_all_strategies() -> Dict[str, Type]:
    """
    Discover all strategy classes that inherit from ParameterizedStrategyMixin.
    Returns a dictionary mapping strategy names to strategy classes.
    """
    return strategy_registry.get_all_strategies()

def get_strategy_parameters(strategy_name: str) -> Dict[str, Any]:
    """
    Get parameter definitions for a specific strategy.
    
    Args:
        strategy_name: Name of the strategy
          Returns:
        Dictionary containing parameter definitions
    """
    strategies = get_all_strategies()
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    strategy_class = strategies[strategy_name]    # Import ParameterizedStrategyMixin dynamically to avoid import path issues
    import importlib
    base_strategy_module = importlib.import_module('src.strategies.base_strategy')
    ParameterizedStrategyMixinDynamic = getattr(base_strategy_module, 'ParameterizedStrategyMixin')
    
    if not issubclass(strategy_class, ParameterizedStrategyMixinDynamic):
        raise ValueError(f"Strategy {strategy_name} does not support parameter definitions")
    
    return strategy_class.get_parameter_definitions_dict()

def get_strategy_defaults(strategy_name: str) -> Dict[str, Any]:
    """
    Get default parameter values for a specific strategy.
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Dictionary containing default parameter values
    """
    strategies = get_all_strategies()
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    strategy_class = strategies[strategy_name]
    
    if not issubclass(strategy_class, ParameterizedStrategyMixin):
        raise ValueError(f"Strategy {strategy_name} does not support parameter definitions")
    
    return strategy_class.get_default_params()

def validate_strategy_parameters(strategy_name: str, params: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate parameters for a specific strategy.
    
    Args:
        strategy_name: Name of the strategy
        params: Dictionary of parameter values to validate
        
    Returns:
        Dictionary mapping parameter names to lists of error messages
    """
    strategies = get_all_strategies()
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    strategy_class = strategies[strategy_name]
    
    if not issubclass(strategy_class, ParameterizedStrategyMixin):
        raise ValueError(f"Strategy {strategy_name} does not support parameter validation")
    
    return strategy_class.validate_params(params)

def get_all_strategy_parameters() -> Dict[str, Dict[str, Any]]:
    """
    Get parameter definitions for all available strategies.
    
    Returns:
        Dictionary mapping strategy names to their parameter definitions
    """
    strategies = get_all_strategies()
    result = {}
    
    for strategy_name, strategy_class in strategies.items():
        if issubclass(strategy_class, ParameterizedStrategyMixin):
            try:
                result[strategy_name] = strategy_class.get_parameter_definitions_dict()
            except Exception as e:
                print(f"Warning: Could not get parameters for {strategy_name}: {e}")
    
    return result

# Example usage functions for app_server.py
def create_parameter_form_data(strategy_name: str) -> Dict[str, Any]:
    """
    Create form data structure suitable for web UI generation.
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Dictionary containing structured form data
    """
    params = get_strategy_parameters(strategy_name)
    
    # Group parameters by category
    categories = {}
    for param_name, param_def in params.items():
        category = param_def.get('category', 'General')
        if category not in categories:
            categories[category] = []
        categories[category].append(param_def)
    
    return {
        'strategy_name': strategy_name,
        'categories': categories,
        'total_parameters': len(params)
    }

def create_backtrader_params(strategy_name: str, user_params: Dict[str, Any]) -> tuple:
    """
    Convert user parameters to Backtrader-compatible params tuple.
    
    Args:
        strategy_name: Name of the strategy
        user_params: Dictionary of user-provided parameter values
        
    Returns:
        Tuple of (param_name, param_value) pairs
    """
    # Get default parameters
    defaults = get_strategy_defaults(strategy_name)
    
    # Merge with user parameters
    final_params = {**defaults, **user_params}
    
    return tuple((name, value) for name, value in final_params.items())
