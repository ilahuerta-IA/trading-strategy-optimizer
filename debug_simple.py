#!/usr/bin/env python3
print("Debug script starting...")

import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
print("Path added successfully")

try:
    from utils.strategy_utils import get_all_strategies
    print("Successfully imported get_all_strategies")
except Exception as e:
    print(f"Error importing get_all_strategies: {e}")
    sys.exit(1)

try:
    from strategies.base_strategy import ParameterizedStrategyMixin
    print("Successfully imported ParameterizedStrategyMixin")
except Exception as e:
    print(f"Error importing ParameterizedStrategyMixin: {e}")
    sys.exit(1)

try:
    strategies = get_all_strategies()
    print(f"Successfully loaded {len(strategies)} strategies")
    
    for name, cls in strategies.items():
        print(f'\nStrategy: {name}')
        print(f'  Class: {cls}')
        print(f'  Is ParameterizedStrategyMixin: {issubclass(cls, ParameterizedStrategyMixin)}')
        if hasattr(cls, '__mro__'):
            print(f'  MRO: {[c.__name__ for c in cls.__mro__]}')
        
except Exception as e:
    print(f"Error getting strategies: {e}")
    import traceback
    traceback.print_exc()
