import pandas as pd
import numpy as np
from typing import List, Dict, Optional

DEFAULT_STACKS = {
    'standard_fbar': {
        'description': 'Standard FBAR: PS/TE/PZ/BE/SD with Mo electrodes',
        'layers': [
            {'name': 'PS', 'terminal': 0, 'thk_nm': 100, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
            {'name': 'TE', 'terminal': 2, 'thk_nm': 240, 'material': 'Mo', 'q_mech': 2000, 'q_die': -99},
            {'name': 'PZ', 'terminal': 0, 'thk_nm': 1000, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
            {'name': 'BE', 'terminal': 1, 'thk_nm': 240, 'material': 'Mo', 'q_mech': 2000, 'q_die': -99},
            {'name': 'SD', 'terminal': 0, 'thk_nm': 25, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
        ]
    },
    
    'minimal_fbar': {
        'description': 'Minimal FBAR: TE/PZ/BE only',
        'layers': [
            {'name': 'TE', 'terminal': 2, 'thk_nm': 240, 'material': 'Mo', 'q_mech': 2000, 'q_die': -99},
            {'name': 'PZ', 'terminal': 0, 'thk_nm': 1000, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
            {'name': 'BE', 'terminal': 1, 'thk_nm': 240, 'material': 'Mo', 'q_mech': 2000, 'q_die': -99},
        ]
    },
    
    'fbar_with_ru': {
        'description': 'FBAR with Ru electrodes',
        'layers': [
            {'name': 'PS', 'terminal': 0, 'thk_nm': 100, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
            {'name': 'TE', 'terminal': 2, 'thk_nm': 200, 'material': 'Ru', 'q_mech': 1500, 'q_die': -99},
            {'name': 'PZ', 'terminal': 0, 'thk_nm': 1000, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
            {'name': 'BE', 'terminal': 1, 'thk_nm': 200, 'material': 'Ru', 'q_mech': 1500, 'q_die': -99},
            {'name': 'SD', 'terminal': 0, 'thk_nm': 25, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
        ]
    },
    
    'smr_basic': {
        'description': 'SMR-BAW with Bragg reflector',
        'layers': [
            {'name': 'PS', 'terminal': 0, 'thk_nm': 100, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
            {'name': 'TE', 'terminal': 2, 'thk_nm': 240, 'material': 'Mo', 'q_mech': 2000, 'q_die': -99},
            {'name': 'PZ', 'terminal': 0, 'thk_nm': 1000, 'material': 'AlN', 'q_mech': 3000, 'q_die': 1000},
            {'name': 'BE', 'terminal': 1, 'thk_nm': 240, 'material': 'Mo', 'q_mech': 2000, 'q_die': -99},
            {'name': 'W1', 'terminal': 0, 'thk_nm': 600, 'material': 'W', 'q_mech': 1000, 'q_die': -99},
            {'name': 'SiO2_1', 'terminal': 0, 'thk_nm': 700, 'material': 'SiO2', 'q_mech': 500, 'q_die': 500},
            {'name': 'W2', 'terminal': 0, 'thk_nm': 600, 'material': 'W', 'q_mech': 1000, 'q_die': -99},
            {'name': 'SiO2_2', 'terminal': 0, 'thk_nm': 700, 'material': 'SiO2', 'q_mech': 500, 'q_die': 500},
        ]
    },
}


# Layer name mapping for user-friendly input
LAYER_ABBREVIATIONS = {
    'PS': 'PS',  # Passivation/Protection Structure
    'TE': 'TE',  # Top Electrode
    'TOP': 'TE',
    'ELECTRODE_TOP': 'TE',
    'PZ': 'PZ',  # PieZoelectric
    'PIEZO': 'PZ',
    'PZL': 'PZ',
    'BE': 'BE',  # Bottom Electrode
    'BOTTOM': 'BE',
    'ELECTRODE_BOTTOM': 'BE',
    'SD': 'SD',  # Seeding/Substrate Device
    'SEED': 'SD',
    'SUBSTRATE': 'SD',
}


def apply_layer_modifications(base_layers: list, modifications: dict) -> list:
    """
    Apply layer modifications to base stack
    
    Args:
        base_layers: List of layer dictionaries
        modifications: Dict of {layer_name: {param: value}}
            e.g., {'PZ': {'thk_nm': 1200}, 'TE': {'material': 'Ru'}}
    
    Returns:
        Modified layer list
    """
    layers = [layer.copy() for layer in base_layers]
    
    for i, layer in enumerate(layers):
        layer_name = layer['name']
        
        # Check direct match
        if layer_name in modifications:
            layers[i].update(modifications[layer_name])
        
        # Check abbreviation match
        elif layer_name in LAYER_ABBREVIATIONS:
            abbr = LAYER_ABBREVIATIONS[layer_name]
            if abbr in modifications:
                layers[i].update(modifications[abbr])
    
    return layers


def create_custom_stack(base_template: str, layer_overrides: dict, 
                        material_lib: pd.DataFrame = None) -> pd.DataFrame:
    """
    Create stack with partial layer overrides
    
    Args:
        base_template: Base template name
        layer_overrides: Dict of layer modifications
        material_lib: Material library DataFrame
    
    Returns:
        Stack info DataFrame
    """
    if base_template not in DEFAULT_STACKS:
        raise ValueError(f"Unknown template: {base_template}")
    
    base_layers = DEFAULT_STACKS[base_template]['layers']
    modified_layers = apply_layer_modifications(base_layers, layer_overrides)
    
    return create_stack_from_dict(modified_layers, material_lib)

