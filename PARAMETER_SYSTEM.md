# Strategy Parameter Definition System

## Overview

This document describes the standardized parameter definition system for Backtrader strategies, which provides structured metadata for easier programmatic access and future UI generation.

## Key Features

1. **Structured Parameter Definitions**: Each parameter includes name, default value, UI label, type, and constraints
2. **Type Safety**: Parameters have defined types (int, float, str, bool) with validation
3. **UI-Ready Metadata**: Includes user-friendly labels, descriptions, and categorization
4. **Validation**: Built-in parameter validation with constraint checking
5. **Backward Compatibility**: Works alongside existing Backtrader `params` tuples

## Usage Example

### Defining Parameters in a Strategy

```python
from .base_strategy import BaseStrategy, ParameterDefinition

class MyStrategy(BaseStrategy):
    
    @classmethod
    def get_parameter_definitions(cls):
        """Define parameters with structured metadata for UI generation."""
        return [
            ParameterDefinition(
                name='fast_period',
                default_value=20,
                ui_label='Fast MA Period',
                param_type='int',
                description='Period for the fast moving average',
                min_value=1,
                max_value=200,
                step=1,
                category='Technical Indicators'
            ),
            ParameterDefinition(
                name='ma_type',
                default_value='SMA',
                ui_label='Moving Average Type',
                param_type='str',
                description='Type of moving average to use',
                choices=['SMA', 'EMA', 'WMA'],
                category='Technical Indicators'
            )
        ]
    
    # Standard Backtrader params tuple (must match parameter definitions)
    params = (
        ('fast_period', 20),
        ('ma_type', 'SMA')
    )
```

### Accessing Parameters from Outside the Strategy

```python
from utils.strategy_utils import get_strategy_parameters, get_strategy_defaults

# Get all parameter definitions
params = get_strategy_parameters('MyStrategy')

# Get default values
defaults = get_strategy_defaults('MyStrategy')

# Validate user parameters
user_params = {'fast_period': 15, 'ma_type': 'EMA'}
errors = validate_strategy_parameters('MyStrategy', user_params)
```

### Using in Flask API (app_server.py)

```python
@app.route('/api/strategies/<strategy_name>/parameters', methods=['GET'])
def get_strategy_params(strategy_name):
    """Get parameter definitions for a specific strategy."""
    try:
        params = get_strategy_parameters(strategy_name)
        form_data = create_parameter_form_data(strategy_name)
        
        return jsonify({
            'success': True,
            'parameters': params,
            'form_data': form_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

## Parameter Definition Fields

### Required Fields

- **name**: Parameter name (must match Backtrader params)
- **default_value**: Default value for the parameter
- **ui_label**: User-friendly display name
- **param_type**: Data type ('int', 'float', 'str', 'bool')

### Optional Fields

- **description**: Detailed explanation of the parameter
- **min_value**: Minimum allowed value (numeric types)
- **max_value**: Maximum allowed value (numeric types)
- **step**: Step size for UI controls (numeric types)
- **choices**: List of valid options (string/enum types)
- **category**: Grouping category for UI organization

## Available Methods

### Class Methods

- `get_parameter_definitions()`: Returns list of ParameterDefinition objects
- `get_parameter_definitions_dict()`: Returns dictionary for JSON serialization
- `get_default_params()`: Returns dictionary of default values
- `validate_params(params_dict)`: Validates parameter values

### Utility Functions

- `get_all_strategies()`: Discover all available strategies
- `get_strategy_parameters(name)`: Get parameters for specific strategy
- `create_parameter_form_data(name)`: Create UI-ready form structure
- `validate_strategy_parameters(name, params)`: Validate parameters

## Implementation Status

### Completed Strategies

1. **CorrelatedSMACrossStrategy**
   - Parameters: p_fast_d0, p_slow_d0, p_fast_d1, p_slow_d1, run_name
   - Categories: Data0 Indicators, Data1 Indicators, General

2. **MACrossOver**
   - Parameters: ma, pd1, pd2, corr_period, cci_period, atr_period, atr_multiplier, cci_exit_level, run_name
   - Categories: Indicators, Correlation, Risk Management, Exit Rules, General

### Next Steps

1. **Add to remaining strategies**: Update `bband_pearson_divergence.py` and any other strategies
2. **UI Integration**: Build web forms based on parameter definitions
3. **Enhanced Validation**: Add custom validation rules for complex constraints
4. **Documentation**: Auto-generate strategy documentation from parameter definitions

## File Structure

```
src/
├── strategies/
│   ├── base_strategy.py              # ParameterDefinition and BaseStrategy classes
│   ├── correlated_sma_cross.py       # Updated with new parameter system
│   └── ma_cci_crossover.py           # Updated with new parameter system
├── utils/
│   └── strategy_utils.py             # Utility functions for parameter access
└── examples/
    └── parameter_system_example.py   # Flask API integration examples
```

## Benefits

1. **Easier UI Generation**: Parameter metadata enables automatic form generation
2. **Better Documentation**: Self-documenting parameters with descriptions and constraints
3. **Improved Validation**: Consistent parameter validation across all strategies
4. **Enhanced Developer Experience**: IDE-friendly parameter access with type hints
5. **Future-Proof**: Easy to extend with additional metadata fields

## Migration Guide

To migrate existing strategies:

1. Import `BaseStrategy` and `ParameterDefinition`
2. Inherit from `BaseStrategy` instead of `bt.Strategy`
3. Add `get_parameter_definitions()` classmethod
4. Keep existing `params` tuple for Backtrader compatibility
5. Test with the validation functions

This system maintains full backward compatibility while adding powerful new capabilities for parameter management and UI generation.
