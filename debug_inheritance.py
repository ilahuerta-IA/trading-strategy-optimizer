#!/usr/bin/env python3
import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.strategy_utils import get_all_strategies
from strategies.base_strategy import ParameterizedStrategyMixin

strategies = get_all_strategies()
print('Strategy classes:')
for name, cls in strategies.items():
    print(f'  {name}: {cls}')
    print(f'  Is ParameterizedStrategyMixin: {issubclass(cls, ParameterizedStrategyMixin)}')
    print(f'  MRO: {[c.__name__ for c in cls.__mro__]}')
    print()
