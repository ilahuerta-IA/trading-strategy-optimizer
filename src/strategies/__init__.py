# strategies/__init__.py
"""
Strategy registration module for dynamic strategy loading.
This module provides a centralized registry of all available strategies.
"""

from typing import Dict, Type, Optional
import importlib

class StrategyRegistry:
    """
    Registry for strategy classes that provides dynamic loading capabilities.
    """
    def __init__(self):
        self._strategies: Dict[str, Dict[str, str]] = {}
        self._loaded_strategies: Dict[str, Type] = {}
        self._register_builtin_strategies()
    
    def _register_builtin_strategies(self):
        """Register built-in strategies with their module and class information."""
        self._strategies.update({
            'CorrelatedSMACross': {
                'module': 'src.strategies.correlated_sma_cross',
                'class': 'CorrelatedSMACrossStrategy',
                'description': 'Correlated SMA Cross Strategy for dual-asset trading'
            },
            'MACrossOver': {
                'module': 'src.strategies.ma_cci_crossover', 
                'class': 'MACrossOver',
                'description': 'Moving Average and CCI Crossover Strategy'
            },
            'BBandPearsonDivergence': {
                'module': 'src.strategies.bband_pearson_divergence',
                'class': 'BBandPearsonDivergence', 
                'description': 'Bollinger Bands Pearson Divergence Strategy'
            }
        })
    
    def register_strategy(self, name: str, module_path: str, class_name: str, description: str = ""):
        """
        Register a new strategy.
        
        Args:
            name: Strategy identifier name
            module_path: Python module path (e.g., 'strategies.my_strategy')
            class_name: Class name within the module
            description: Strategy description
        """
        self._strategies[name] = {
            'module': module_path,
            'class': class_name,
            'description': description
        }
        # Clear cached strategy if it exists
        if name in self._loaded_strategies:
            del self._loaded_strategies[name]
    
    def get_strategy_names(self) -> list:
        """Get list of all registered strategy names."""
        return list(self._strategies.keys())
    
    def get_strategy_info(self, name: str) -> Optional[Dict[str, str]]:
        """Get strategy registration information."""
        return self._strategies.get(name)
    
    def load_strategy(self, name: str) -> Type:
        """
        Dynamically load and return a strategy class.
        
        Args:
            name: Strategy name to load
            
        Returns:
            Strategy class
            
        Raises:
            ValueError: If strategy name is not registered
            ImportError: If strategy module cannot be imported
            AttributeError: If strategy class is not found in module
        """
        if name not in self._strategies:
            available = ', '.join(self._strategies.keys())
            raise ValueError(f"Unknown strategy '{name}'. Available strategies: {available}")
        
        # Return cached strategy if already loaded
        if name in self._loaded_strategies:
            return self._loaded_strategies[name]
        
        strategy_info = self._strategies[name]
        module_path = strategy_info['module']
        class_name = strategy_info['class']
        
        try:
            # Import the strategy module
            strategy_module = importlib.import_module(module_path)
              # Get the strategy class from the module
            strategy_class = getattr(strategy_module, class_name)
            
            # Validate that it's a strategy class
            # Import BaseStrategy dynamically to avoid circular imports
            base_strategy_module = importlib.import_module('src.strategies.base_strategy')
            BaseStrategy = getattr(base_strategy_module, 'BaseStrategy')
            
            if not issubclass(strategy_class, BaseStrategy):
                raise TypeError(f"Class {class_name} is not a subclass of BaseStrategy")
            
            # Cache the loaded strategy
            self._loaded_strategies[name] = strategy_class
            
            return strategy_class
            
        except ImportError as e:
            raise ImportError(f"Could not import strategy module '{module_path}': {e}")
        except AttributeError as e:
            raise AttributeError(f"Strategy class '{class_name}' not found in module '{module_path}': {e}")
    
    def is_strategy_available(self, name: str) -> bool:
        """Check if a strategy is available for loading."""
        try:
            self.load_strategy(name)
            return True
        except (ValueError, ImportError, AttributeError):
            return False
    
    def get_all_strategies(self) -> Dict[str, Type]:
        """
        Load and return all available strategies.
        
        Returns:
            Dictionary mapping strategy names to strategy classes
        """
        strategies = {}
        for name in self._strategies.keys():
            try:
                strategies[name] = self.load_strategy(name)
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not load strategy '{name}': {e}")
        return strategies

# Global strategy registry instance
strategy_registry = StrategyRegistry()

# Convenience functions for backwards compatibility
def get_strategy_class(name: str) -> Type:
    """Get a strategy class by name."""
    return strategy_registry.load_strategy(name)

def get_available_strategies() -> Dict[str, Type]:
    """Get all available strategy classes."""
    return strategy_registry.get_all_strategies()

def register_strategy(name: str, module_path: str, class_name: str, description: str = ""):
    """Register a new strategy."""
    strategy_registry.register_strategy(name, module_path, class_name, description)

def list_strategy_names() -> list:
    """Get list of all registered strategy names."""
    return strategy_registry.get_strategy_names()

# Export the registry and functions
__all__ = [
    'StrategyRegistry',
    'strategy_registry', 
    'get_strategy_class',
    'get_available_strategies',
    'register_strategy',
    'list_strategy_names'
]
