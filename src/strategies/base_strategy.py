from typing import Dict, List, Union, Optional, Any
from dataclasses import dataclass

@dataclass
class ParameterDefinition:
    """Structured definition of a strategy parameter for UI generation and validation."""
    name: str
    default_value: Any
    ui_label: str
    type: str  # 'int', 'float', 'str', 'bool'
    description: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    group: Optional[str] = None  # For organizing parameters in UI sections

class ParameterizedStrategy:
    """Mixin class providing standardized parameter definitions for strategies."""
    
    @classmethod
    def get_parameter_definitions(cls) -> List[ParameterDefinition]:
        """
        Override this method in strategy classes to define parameter metadata.
        Must return a list of ParameterDefinition objects.
        """
        return []
    
    @classmethod
    def get_parameter_dict(cls) -> Dict[str, ParameterDefinition]:
        """Returns parameter definitions as a dictionary keyed by parameter name."""
        return {param.name: param for param in cls.get_parameter_definitions()}
    
    @classmethod
    def validate_parameters(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and converts parameter values according to their definitions.
        Returns the validated/converted parameters.
        """
        param_defs = cls.get_parameter_dict()
        validated = {}
        
        for name, value in params.items():
            if name not in param_defs:
                validated[name] = value  # Pass through unknown params
                continue
                
            param_def = param_defs[name]
            
            # Type conversion
            if param_def.type == 'int':
                validated[name] = int(value)
            elif param_def.type == 'float':
                validated[name] = float(value)
            elif param_def.type == 'bool':
                validated[name] = bool(value) if not isinstance(value, str) else value.lower() in ('true', '1', 'yes')
            else:
                validated[name] = str(value)
            
            # Range validation for numeric types
            if param_def.type in ('int', 'float'):
                if param_def.min_value is not None and validated[name] < param_def.min_value:
                    validated[name] = param_def.min_value
                if param_def.max_value is not None and validated[name] > param_def.max_value:
                    validated[name] = param_def.max_value
            
            # Choice validation
            if param_def.choices and validated[name] not in param_def.choices:
                validated[name] = param_def.default_value
        
        return validated