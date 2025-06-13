# test_strategy_registry.py
"""
Test script to verify the strategy registry and dynamic loading system works correctly.
"""

import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_strategy_registry():
    """Test the strategy registry functionality."""
    print("=== Testing Strategy Registry ===")
    
    try:
        from strategies import strategy_registry, get_strategy_class, list_strategy_names
        
        # Test getting strategy names
        print("1. Getting available strategy names...")
        strategy_names = list_strategy_names()
        print(f"   Available strategies: {strategy_names}")
        
        # Test loading each strategy
        print("\n2. Testing dynamic strategy loading...")
        for strategy_name in strategy_names:
            try:
                strategy_class = get_strategy_class(strategy_name)
                print(f"   ✓ Successfully loaded {strategy_name}: {strategy_class.__name__}")
                
                # Test parameter definitions
                param_defs = strategy_class.get_parameter_definitions()
                print(f"     - Has {len(param_defs)} parameters")
                
            except Exception as e:
                print(f"   ✗ Failed to load {strategy_name}: {e}")
        
        # Test error handling for unknown strategy
        print("\n3. Testing error handling...")
        try:
            unknown_strategy = get_strategy_class('UnknownStrategy')
            print("   ✗ Should have failed for unknown strategy")
        except ValueError as e:
            print(f"   ✓ Correctly handled unknown strategy: {e}")
        
        # Test strategy availability check
        print("\n4. Testing strategy availability...")
        for strategy_name in strategy_names:
            is_available = strategy_registry.is_strategy_available(strategy_name)
            print(f"   {strategy_name}: {'Available' if is_available else 'Not Available'}")
        
        print("\n✓ Strategy registry tests passed!")
        
    except Exception as e:
        print(f"✗ Strategy registry tests failed: {e}")
        import traceback
        traceback.print_exc()

def test_integration_with_backtrader():
    """Test that loaded strategies work with Backtrader."""
    print("\n=== Testing Backtrader Integration ===")
    
    try:
        import backtrader as bt
        from strategies import get_strategy_class
        
        # Test creating a cerebro instance with a dynamically loaded strategy
        print("1. Testing strategy instantiation with Backtrader...")
        
        strategy_class = get_strategy_class('CorrelatedSMACross')
        
        # Create a minimal cerebro instance
        cerebro = bt.Cerebro()
        
        # Add the strategy with custom parameters
        custom_params = {
            'p_fast_d0': 15,
            'p_slow_d0': 45,
            'run_name': 'test_dynamic_load'
        }
        
        cerebro.addstrategy(strategy_class, **custom_params)
        print("   ✓ Successfully added strategy to Cerebro")
        
        # Test that the strategy has the correct parameters
        strategies = cerebro.runstrats
        if strategies:
            strategy_params = strategies[0][0]
            print(f"   ✓ Strategy parameters configured: {dict(strategy_params.params._getpairs())}")
        
        print("✓ Backtrader integration tests passed!")
        
    except Exception as e:
        print(f"✗ Backtrader integration tests failed: {e}")
        import traceback
        traceback.print_exc()

def test_parameter_system_integration():
    """Test integration between strategy registry and parameter system."""
    print("\n=== Testing Parameter System Integration ===")
    
    try:
        from strategies import get_strategy_class
        from utils.strategy_utils import get_strategy_parameters, validate_strategy_parameters
        
        print("1. Testing parameter access through both systems...")
        
        # Test each strategy
        strategy_names = ['CorrelatedSMACross', 'MACrossOver', 'BBandPearsonDivergence']
        
        for strategy_name in strategy_names:
            print(f"\n   Testing {strategy_name}:")
            
            # Load via registry
            strategy_class = get_strategy_class(strategy_name)
            registry_params = strategy_class.get_parameter_definitions_dict()
            
            # Load via utils
            utils_params = get_strategy_parameters(strategy_name)
            
            # Compare
            if registry_params.keys() == utils_params.keys():
                print(f"     ✓ Parameter consistency: {len(registry_params)} parameters")
            else:
                print(f"     ✗ Parameter mismatch: Registry={list(registry_params.keys())}, Utils={list(utils_params.keys())}")
            
            # Test validation
            test_params = {list(registry_params.keys())[0]: 'invalid_value'}
            errors = validate_strategy_parameters(strategy_name, test_params)
            if errors:
                print(f"     ✓ Validation working: {len(errors)} errors detected")
            else:
                print(f"     ? Validation may not be working properly")
        
        print("\n✓ Parameter system integration tests passed!")
        
    except Exception as e:
        print(f"✗ Parameter system integration tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Testing Strategy Registry and Dynamic Loading System")
    print("=" * 60)
    
    test_strategy_registry()
    test_integration_with_backtrader()
    test_parameter_system_integration()
    
    print("\n" + "=" * 60)
    print("Registry testing complete!")
