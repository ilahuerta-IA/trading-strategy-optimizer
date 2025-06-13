# Example usage in app_server.py
"""
This example shows how to integrate the new parameter definition system
into your Flask app for UI generation and parameter validation.
"""

from flask import Flask, request, jsonify
from utils.strategy_utils import (
    get_all_strategies,
    get_strategy_parameters,
    get_strategy_defaults,
    validate_strategy_parameters,
    create_parameter_form_data,
    create_backtrader_params
)

app = Flask(__name__)

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """Get list of available strategies."""
    try:
        strategies = get_all_strategies()
        strategy_list = []
        
        for name, strategy_class in strategies.items():
            strategy_list.append({
                'name': name,
                'class_name': strategy_class.__name__,
                'description': strategy_class.__doc__ or '',
                'parameter_count': len(strategy_class.get_parameter_definitions())
            })
        
        return jsonify({
            'success': True,
            'strategies': strategy_list
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/<strategy_name>/defaults', methods=['GET'])
def get_strategy_param_defaults(strategy_name):
    """Get default parameter values for a specific strategy."""
    try:
        defaults = get_strategy_defaults(strategy_name)
        
        return jsonify({
            'success': True,
            'defaults': defaults
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/<strategy_name>/validate', methods=['POST'])
def validate_strategy_params(strategy_name):
    """Validate parameter values for a specific strategy."""
    try:
        params = request.json.get('parameters', {})
        errors = validate_strategy_parameters(strategy_name, params)
        
        return jsonify({
            'success': len(errors) == 0,
            'errors': errors,
            'valid': len(errors) == 0
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/<strategy_name>/run', methods=['POST'])
def run_strategy(strategy_name):
    """Run a strategy with specified parameters."""
    try:
        user_params = request.json.get('parameters', {})
        
        # Validate parameters
        errors = validate_strategy_parameters(strategy_name, user_params)
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Create Backtrader-compatible parameters
        bt_params = create_backtrader_params(strategy_name, user_params)
        
        # Here you would integrate with your existing backtest runner
        # For example:
        # result = run_backtest(strategy_name, bt_params)
        
        # Simulated response for this example
        result = {
            'message': f'Strategy {strategy_name} executed successfully',
            'parameters_used': dict(bt_params),
            'backtest_id': 'example_123'
        }
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Example of how to use in your existing backtest runner
def run_backtest_with_new_params(strategy_name, user_params):
    """
    Example function showing how to integrate with existing backtest code.
    """
    from strategies.correlated_sma_cross import CorrelatedSMACrossStrategy
    import backtrader as bt
    
    # Get the strategy class
    strategies = get_all_strategies()
    strategy_class = strategies[strategy_name]
    
    # Validate parameters
    errors = validate_strategy_parameters(strategy_name, user_params)
    if errors:
        raise ValueError(f"Parameter validation failed: {errors}")
    
    # Create Backtrader params
    bt_params = create_backtrader_params(strategy_name, user_params)
    
    # Create cerebro and add strategy with parameters
    cerebro = bt.Cerebro()
    
    # Dynamically set strategy parameters
    strategy_kwargs = dict(bt_params)
    cerebro.addstrategy(strategy_class, **strategy_kwargs)
    
    # Add data, run backtest, etc.
    # ... your existing backtest code ...
    
    return cerebro.run()

if __name__ == '__main__':
    # Example usage
    print("Available strategies:")
    strategies = get_all_strategies()
    for name in strategies.keys():
        print(f"  - {name}")
    
    # Example: Get parameters for CorrelatedSMACross
    print("\nCorrelatedSMACross parameters:")
    params = get_strategy_parameters('CorrelatedSMACross')
    for param_name, param_def in params.items():
        print(f"  {param_name}: {param_def['ui_label']} (default: {param_def['default_value']})")
    
    # Example: Validate some parameters
    print("\nValidating parameters:")
    test_params = {
        'p_fast_d0': 15,
        'p_slow_d0': 45,
        'p_fast_d1': 25,
        'p_slow_d1': 55,
        'run_name': 'test_run'
    }
    errors = validate_strategy_parameters('CorrelatedSMACross', test_params)
    if errors:
        print(f"  Validation errors: {errors}")
    else:
        print("  All parameters valid!")
    
    app.run(debug=True)
