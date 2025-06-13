# strategies/base_strategy.py
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import backtrader as bt

@dataclass
class ParameterDefinition:
    """
    Structured definition for a strategy parameter.
    """
    name: str
    default_value: Any
    ui_label: str
    param_type: str  # 'int', 'float', 'str', 'bool'
    description: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    category: Optional[str] = None  # For grouping parameters in UI
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'default_value': self.default_value,
            'ui_label': self.ui_label,
            'type': self.param_type,
            'description': self.description,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'step': self.step,
            'choices': self.choices,
            'category': self.category
        }
    
    def validate_value(self, value: Any) -> bool:
        """Validate a value against this parameter's constraints."""
        if self.param_type == 'int':
            if not isinstance(value, int):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        elif self.param_type == 'float':
            if not isinstance(value, (int, float)):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        elif self.param_type == 'str':
            if not isinstance(value, str):
                return False
            if self.choices and value not in self.choices:
                return False
        elif self.param_type == 'bool':
            if not isinstance(value, bool):
                return False
        return True

class ParameterizedStrategyMixin:
    """
    Mixin class that provides standardized parameter definition capabilities.
    """
    
    @classmethod
    def get_parameter_definitions(cls) -> List[ParameterDefinition]:
        """
        Override this method in strategy classes to define parameters.
        Returns a list of ParameterDefinition objects.
        """
        raise NotImplementedError("Subclasses must implement get_parameter_definitions()")
    
    @classmethod
    def get_parameter_definitions_dict(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get parameter definitions as a dictionary for easy serialization.
        """
        definitions = cls.get_parameter_definitions()
        return {param.name: param.to_dict() for param in definitions}
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """
        Get default parameter values as a dictionary.
        """
        definitions = cls.get_parameter_definitions()
        return {param.name: param.default_value for param in definitions}
    
    @classmethod
    def validate_params(cls, params_dict: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate a dictionary of parameters against the definitions.
        Returns a dictionary of parameter names to lists of error messages.
        """
        definitions = {param.name: param for param in cls.get_parameter_definitions()}
        errors = {}
        
        for param_name, value in params_dict.items():
            if param_name not in definitions:
                errors.setdefault(param_name, []).append(f"Unknown parameter: {param_name}")
                continue
            
            param_def = definitions[param_name]
            if not param_def.validate_value(value):
                errors.setdefault(param_name, []).append(
                    f"Invalid value for {param_name}: {value}"
                )
        
        return errors
    
    @classmethod
    def get_backtrader_params(cls) -> tuple:
        """
        Convert parameter definitions to Backtrader-compatible params tuple.
        """
        definitions = cls.get_parameter_definitions()
        return tuple((param.name, param.default_value) for param in definitions)

class BaseStrategy(bt.Strategy, ParameterizedStrategyMixin):
    """
    Base strategy class that combines Backtrader Strategy with parameter management.
    """
    pass
