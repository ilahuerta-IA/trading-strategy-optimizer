# test_parameter_system.py
"""
Test script to verify the new parameter definition system works correctly.
"""

import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_correlated_sma_strategy():
    """Test the CorrelatedSMACrossStrategy parameter system."""
    print("=== Testing CorrelatedSMACrossStrategy ===")
    
    try:
        from strategies.correlated_sma_cross import CorrelatedSMACrossStrategy
        
        # Test parameter definitions
        print("1. Getting parameter definitions...")
        param_defs = CorrelatedSMACrossStrategy.get_parameter_definitions()
        print(f"   Found {len(param_defs)} parameters")
        
        for param in param_defs:
            print(f"   - {param.name}: {param.ui_label} (default: {param.default_value})")
        
        # Test parameter definitions as dict
        print("\n2. Getting parameter definitions as dict...")
        param_dict = CorrelatedSMACrossStrategy.get_parameter_definitions_dict()
        print(f"   Dict keys: {list(param_dict.keys())}")
        
        # Test default params
        print("\n3. Getting default parameters...")
        defaults = CorrelatedSMACrossStrategy.get_default_params()
        print(f"   Defaults: {defaults}")
        
        # Test validation
        print("\n4. Testing parameter validation...")
        valid_params = {
            'p_fast_d0': 15,
            'p_slow_d0': 45,
            'p_fast_d1': 25,
            'p_slow_d1': 55,
            'run_name': 'test_run'
        }
        errors = CorrelatedSMACrossStrategy.validate_params(valid_params)
        print(f"   Valid params errors: {errors}")
        
        invalid_params = {
            'p_fast_d0': -5,  # Invalid: below min_value
            'p_slow_d0': 1000,  # Invalid: above max_value
            'unknown_param': 123  # Invalid: unknown parameter
        }
        errors = CorrelatedSMACrossStrategy.validate_params(invalid_params)
        print(f"   Invalid params errors: {errors}")
        
        # Test Backtrader params generation
        print("\n5. Testing Backtrader params generation...")
        bt_params = CorrelatedSMACrossStrategy.params
        print(f"   Backtrader params: {bt_params}")
        
        print("✓ CorrelatedSMACrossStrategy tests passed!")
        
    except Exception as e:
        print(f"✗ CorrelatedSMACrossStrategy tests failed: {e}")
        import traceback
        traceback.print_exc()

def test_ma_cci_strategy():
    """Test the MACrossOver strategy parameter system."""
    print("\n=== Testing MACrossOver Strategy ===")
    
    try:
        from strategies.ma_cci_crossover import MACrossOver
        
        # Test parameter definitions
        print("1. Getting parameter definitions...")
        param_defs = MACrossOver.get_parameter_definitions()
        print(f"   Found {len(param_defs)} parameters")
        
        for param in param_defs:
            print(f"   - {param.name}: {param.ui_label} (default: {param.default_value})")
        
        # Test parameter categorization
        print("\n2. Testing parameter categorization...")
        param_dict = MACrossOver.get_parameter_definitions_dict()
        categories = {}
        for param_name, param_def in param_dict.items():
            category = param_def.get('category', 'General')
            categories.setdefault(category, []).append(param_name)
        
        for category, params in categories.items():
            print(f"   {category}: {params}")
        
        print("✓ MACrossOver tests passed!")
        
    except Exception as e:
        print(f"✗ MACrossOver tests failed: {e}")
        import traceback
        traceback.print_exc()

def test_strategy_utils():
    """Test the strategy utility functions."""
    print("\n=== Testing Strategy Utils ===")
    
    try:
        from utils.strategy_utils import (
            get_all_strategies,
            get_strategy_parameters,
            create_parameter_form_data
        )
        
        print("1. Getting all strategies...")
        strategies = get_all_strategies()
        print(f"   Found strategies: {list(strategies.keys())}")
        
        if 'CorrelatedSMACross' in strategies:
            print("\n2. Getting parameters for CorrelatedSMACross...")
            params = get_strategy_parameters('CorrelatedSMACross')
            print(f"   Parameter count: {len(params)}")
            
            print("\n3. Creating form data...")
            form_data = create_parameter_form_data('CorrelatedSMACross')
            print(f"   Categories: {list(form_data['categories'].keys())}")
            print(f"   Total parameters: {form_data['total_parameters']}")
        
        print("✓ Strategy utils tests passed!")
        
    except Exception as e:
        print(f"✗ Strategy utils tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Testing Parameter Definition System")
    print("=" * 50)
    
    test_correlated_sma_strategy()
    test_ma_cci_strategy()
    test_strategy_utils()
    
    print("\n" + "=" * 50)
    print("Testing complete!")
