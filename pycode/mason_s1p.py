
"""
BAW Resonator S1P Generator using Mason Model
Supports default templates with partial layer overrides
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
import os
import json
from typing import Dict, Optional, Tuple, List, Union
from pathlib import Path

# Import stack templates
from stack_templates import DEFAULT_STACKS, apply_layer_modifications, LAYER_ABBREVIATIONS

try:
    import skrf as rf
    SKRF_AVAILABLE = True
except ImportError:
    SKRF_AVAILABLE = False


class Material:
    """BAW material properties"""
    def __init__(self, name: str, rho: float, c33: complex, e33: float, eps33: complex):
        self.name = name
        self.rho = rho
        self.c33 = c33
        self.e33 = e33
        self.eps33 = eps33

    def velocity(self) -> float:
        if self.eps33 == 0:
            K2 = 0
        else:
            K2 = self.e33**2 / (self.c33 * self.eps33)
        c33D = self.c33 * (1 + K2)
        return np.sqrt(c33D / self.rho)

    def impedance(self) -> float:
        if self.eps33 == 0:
            K2 = 0
        else:
            K2 = self.e33**2 / (self.c33 * self.eps33)
        c33D = self.c33 * (1 + K2)
        return np.sqrt(c33D * self.rho)


def load_material_library(lib_path: Optional[str] = None) -> pd.DataFrame:
    """Load material library"""
    if lib_path and os.path.exists(lib_path):
        return pd.read_excel(lib_path, sheet_name='MHB_<3GHz')
    
    # Default materials (MHB parameters)
    default_data = {
        'Material': ['Mo', 'AlN', 'Ru', 'W', 'SiO2', 'Ti'],
        'rho_kg_m3': [10200.0, 3343.0, 12177.0, 19250.0, 2200.0, 4540.0],
        'c33_Pa': [4.49e11, 3.89e11, 6.24e11, 6.0e11, 7.64e10, 2.39e11],
        'e33_C_m2': [0.0, 1.46, 0.0, 0.0, 0.0, 0.0],
        'eps33_F_m': [0.0, 8.88e-11, 0.0, 0.0, 0.0, 0.0],
        'Q_Mech': [2000, 3713, 1000, 1000, 500, -99],
        'Q_Die': [-99, 527, -99, -99, 500, -99]
    }
    return pd.DataFrame(default_data)


def create_stack_from_dict(layers: List[Dict], material_lib: pd.DataFrame) -> pd.DataFrame:
    """Create stack_info DataFrame from layer definitions"""
    data = {
        'Layer_Name': [], 'Terminal': [], 'THK': [],
        'Material': [], 'rho': [], 'c33': [], 'e33': [], 'eps33': []
    }
    
    for layer in layers:
        mat_name = layer['material']
        mat_rows = material_lib[material_lib['Material'] == mat_name]
        if len(mat_rows) == 0:
            raise ValueError(f"Material {mat_name} not found in library")
        mat_row = mat_rows.iloc[0]
        
        q_mech = layer.get('q_mech', -99)
        q_die = layer.get('q_die', -99)
        Q_Mech = np.inf if q_mech == -99 else q_mech
        Q_Die = np.inf if q_die == -99 else q_die
        
        data['Layer_Name'].append(layer['name'])
        data['Terminal'].append(layer['terminal'])
        data['THK'].append(layer['thk_nm'])
        data['Material'].append(mat_name)
        data['rho'].append(mat_row['rho_kg_m3'])
        data['c33'].append(mat_row['c33_Pa'] * (1 + 1j/Q_Mech))
        data['e33'].append(mat_row.get('e33_C_m2', 0))
        
        eps_val = mat_row.get('eps33_F_m', 0)
        data['eps33'].append(eps_val * (1 - 1j/Q_Die) if eps_val != 0 else 0)
    
    return pd.DataFrame(data)


def z_matrix_elastic(mat: Material, d: float, A: float, w: np.ndarray) -> np.ndarray:
    """2-port impedance matrix for elastic material"""
    k = w / mat.velocity()
    ZT = mat.impedance() * A
    z11 = ZT / (1j * np.tan(k * d))
    z12 = ZT / (1j * np.sin(k * d))
    
    Z = np.zeros((2, 2, len(w)), dtype=np.complex128)
    Z[0, 0, :] = z11
    Z[0, 1, :] = z12
    Z[1, 0, :] = z12
    Z[1, 1, :] = z11
    return Z


def z_matrix_piezo(mat: Material, d: float, A: float, w: np.ndarray):
    """3-port impedance matrix for piezoelectric material"""
    k = w / mat.velocity()
    ZT = mat.impedance() * A
    h = mat.e33 / mat.eps33 if mat.eps33 != 0 else 0
    C0 = mat.eps33 * A / d
    
    z11 = ZT / (1j * np.tan(k * d))
    z12 = ZT / (1j * np.sin(k * d))
    z13 = h / (1j * w)
    z33 = 1 / (1j * w * C0)
    
    Z = np.zeros((3, 3, len(w)), dtype=np.complex128)
    Z[0, 0, :] = z11
    Z[0, 1, :] = z12
    Z[0, 2, :] = z13
    Z[1, 0, :] = z12
    Z[1, 1, :] = z11
    Z[1, 2, :] = z13
    Z[2, 0, :] = z13
    Z[2, 1, :] = z13
    Z[2, 2, :] = z33
    return Z, C0


def z2abcd(Z: np.ndarray) -> np.ndarray:
    """Convert Z matrix to ABCD matrix"""
    detZ = Z[0, 0, :] * Z[1, 1, :] - Z[0, 1, :] * Z[1, 0, :]
    T = np.zeros((2, 2, Z.shape[2]), dtype=np.complex128)
    T[0, 0, :] = Z[0, 0, :] / Z[1, 0, :]
    T[0, 1, :] = detZ / Z[1, 0, :]
    T[1, 0, :] = 1 / Z[1, 0, :]
    T[1, 1, :] = Z[1, 1, :] / Z[1, 0, :]
    return T


def t_matrix_elastic(mat: Material, d: float, A: float, w: np.ndarray) -> np.ndarray:
    """ABCD matrix for elastic material"""
    Z = z_matrix_elastic(mat, d, A, w)
    return z2abcd(Z)


def adaptive_mason(stack_info: pd.DataFrame, A: float, w: np.ndarray):
    """Mason model main function"""
    # Bottom transmission line (from bottom electrode down)
    terminal_1 = np.where(stack_info.Terminal == 1)[0][0]
    for idx in range(terminal_1, stack_info.shape[0]):
        mat = Material(name=stack_info.Material[idx], rho=stack_info.rho[idx],
                      c33=stack_info.c33[idx], e33=0, eps33=0)
        thk = stack_info.THK[idx] * 1e-9
        if idx == terminal_1:
            Tb = t_matrix_elastic(mat, thk, A, w)
        else:
            T_mid = t_matrix_elastic(mat, thk, A, w)
            c11 = Tb[0,0,:]*T_mid[0,0,:] + Tb[0,1,:]*T_mid[1,0,:]
            c12 = Tb[0,0,:]*T_mid[0,1,:] + Tb[0,1,:]*T_mid[1,1,:]
            c21 = Tb[1,0,:]*T_mid[0,0,:] + Tb[1,1,:]*T_mid[1,0,:]
            c22 = Tb[1,0,:]*T_mid[0,1,:] + Tb[1,1,:]*T_mid[1,1,:]
            Tb[0,0,:] = c11
            Tb[0,1,:] = c12
            Tb[1,0,:] = c21
            Tb[1,1,:] = c22

    # Top transmission line (from top electrode up)
    terminal_2 = np.where(stack_info.Terminal == 2)[0][0]
    for idx in range(terminal_2, -1, -1):
        mat = Material(name=stack_info.Material[idx], rho=stack_info.rho[idx],
                      c33=stack_info.c33[idx], e33=0, eps33=0)
        thk = stack_info.THK[idx] * 1e-9
        if idx == terminal_2:
            Tt = t_matrix_elastic(mat, thk, A, w)
        else:
            T_mid = t_matrix_elastic(mat, thk, A, w)
            c11 = Tt[0,0,:]*T_mid[0,0,:] + Tt[0,1,:]*T_mid[1,0,:]
            c12 = Tt[0,0,:]*T_mid[0,1,:] + Tt[0,1,:]*T_mid[1,1,:]
            c21 = Tt[1,0,:]*T_mid[0,0,:] + Tt[1,1,:]*T_mid[1,0,:]
            c22 = Tt[1,0,:]*T_mid[0,1,:] + Tt[1,1,:]*T_mid[1,1,:]
            Tt[0,0,:] = c11
            Tt[0,1,:] = c12
            Tt[1,0,:] = c21
            Tt[1,1,:] = c22

    # Piezoelectric layer
    for idx in range(terminal_1 - 1, terminal_2, -1):
        mat = Material(name=stack_info.Material[idx], rho=stack_info.rho[idx],
                      c33=stack_info.c33[idx], e33=stack_info.e33[idx],
                      eps33=stack_info.eps33[idx])
        thk = stack_info.THK[idx] * 1e-9
        
        if idx == terminal_1 - 1:
            Zp, C0 = z_matrix_piezo(mat, thk, A, w)
            C0 = np.real(C0)
        else:
            Zp2, C02 = z_matrix_piezo(mat, thk, A, w)
            C0 = 1 / (1/C0 + 1/np.real(C02))
            
            # Combine impedance matrices
            Zp12 = np.zeros((3, 3, len(w)), dtype=np.complex128)
            denom = -Zp[1,1,:] - Zp2[0,0,:]
            Zp12[0,0,:] = Zp[0,0,:] + (Zp[0,1,:]*Zp[1,0,:])/denom
            Zp12[0,1,:] = (-Zp[0,1,:]*Zp2[0,1,:])/denom
            Zp12[0,2,:] = Zp[0,2,:] - Zp[0,1,:]*(Zp2[0,2,:]-Zp[1,2,:])/denom
            Zp12[1,0,:] = (-Zp2[1,0,:]*Zp[1,0,:])/denom
            Zp12[1,1,:] = Zp2[1,1,:] + (Zp2[1,0,:]*Zp2[0,1,:])/denom
            Zp12[1,2,:] = Zp2[1,2,:] + Zp2[1,0,:]*(Zp2[0,2,:]-Zp[1,2,:])/denom
            Zp12[2,0,:] = Zp[2,0,:] - Zp[1,0,:]*(Zp2[2,0,:]-Zp[2,1,:])/denom
            Zp12[2,1,:] = Zp2[2,1,:] + Zp2[0,1,:]*(Zp2[2,0,:]-Zp[2,1,:])/denom
            Zp12[2,2,:] = Zp[2,2,:] + Zp2[2,2,:] + (Zp2[2,0,:]-Zp[2,1,:])*(Zp2[0,2,:]-Zp[1,2,:])/denom
            Zp = Zp12

    # Assemble final impedance matrix
    X = np.zeros((3, 3, len(w)), dtype=np.complex128)
    X[0,0,:] = -Zp[0,0,:]*Tb[1,1,:] - Tb[0,1,:]
    X[0,1,:] = -Zp[0,1,:]*Tt[1,1,:]
    X[0,2,:] = Zp[0,2,:]
    X[1,0,:] = -Zp[1,0,:]*Tb[1,1,:]
    X[1,1,:] = -Zp[1,1,:]*Tt[1,1,:] - Tt[0,1,:]
    X[1,2,:] = Zp[1,2,:]
    X[2,0,:] = -Zp[2,0,:]*Tb[1,1,:]
    X[2,1,:] = -Zp[2,1,:]*Tt[1,1,:]
    X[2,2,:] = Zp[2,2,:]

    return X, C0


def mason_fbar(stack_info: pd.DataFrame, A: float, w: np.ndarray, Rs: float = 0.0):
    """Calculate impedance for FBAR"""
    Z, C0 = adaptive_mason(stack_info, A, w)
    Z_mason = np.zeros(len(w), dtype=np.complex128)
    
    for idx in range(len(w)):
        temp = Z[1,0,idx]*Z[0,1,idx] - Z[0,0,idx]*Z[1,1,idx]
        temp2 = Z[2,0,idx]*(Z[1,1,idx]*Z[0,2,idx]-Z[0,1,idx]*Z[1,2,idx]) + \
                Z[2,1,idx]*(Z[0,0,idx]*Z[1,2,idx]-Z[1,0,idx]*Z[0,2,idx])
        Z_mason[idx] = Z[2,2,idx] + temp2/temp
    
    return Z_mason + Rs, C0


class MasonS1PGenerator:
    """BAW S1P Generator with template and partial override support"""
    
    def __init__(self):
        self.stack_info = None
        self.results = None
        self.frequency = None
        self.impedance = None
        self.C0 = None
        self.material_lib = None
    
    def load_material_library(self, lib_path: Optional[str] = None):
        """Load material library"""
        self.material_lib = load_material_library(lib_path)
    
    def use_template(self, template: str, layer_overrides: Optional[Dict] = None):
        """
        Use template with optional layer overrides
        
        Args:
            template: Template name ('standard_fbar', 'minimal_fbar', 'fbar_with_ru', 'smr_basic')
            layer_overrides: Dict of {layer_name: {param: value}}
                e.g., {'PZ': {'thk_nm': 1200}, 'TE': {'material': 'Ru'}}
        """
        if template not in DEFAULT_STACKS:
            available = ', '.join(DEFAULT_STACKS.keys())
            raise ValueError(f"Unknown template: {template}. Available: {available}")
        
        if self.material_lib is None:
            self.load_material_library()
        
        base_layers = DEFAULT_STACKS[template]['layers']
        
        if layer_overrides:
            layers = apply_layer_modifications(base_layers, layer_overrides)
            print(f"Using template: {DEFAULT_STACKS[template]['description']}")
            print(f"Applied overrides: {list(layer_overrides.keys())}")
        else:
            layers = base_layers
            print(f"Using template: {DEFAULT_STACKS[template]['description']}")
        
        self.stack_info = create_stack_from_dict(layers, self.material_lib)
        self._print_stack()
    
    def override_layers(self, layer_dict: Dict[str, Dict]):
        """
        Override specific layers in current stack
        
        Args:
            layer_dict: e.g., {'PZ': {'thk_nm': 1100, 'material': 'AlN'}}
        """
        if self.stack_info is None:
            raise ValueError("No stack loaded. Call use_template() first.")
        
        for layer_name, params in layer_dict.items():
            mask = self.stack_info['Layer_Name'] == layer_name
            if not mask.any():
                # Try abbreviations
                if layer_name in LAYER_ABBREVIATIONS:
                    abbr = LAYER_ABBREVIATIONS[layer_name]
                    mask = self.stack_info['Layer_Name'] == abbr
            
            if mask.any():
                idx = self.stack_info[mask].index[0]
                for param, value in params.items():
                    if param == 'thk_nm':
                        self.stack_info.at[idx, 'THK'] = value
                    elif param == 'material':
                        self.stack_info.at[idx, 'Material'] = value
                        # Update material properties
                        mat_row = self.material_lib[self.material_lib['Material'] == value].iloc[0]
                        self.stack_info.at[idx, 'rho'] = mat_row['rho_kg_m3']
                        self.stack_info.at[idx, 'c33'] = mat_row['c33_Pa']
                        self.stack_info.at[idx, 'e33'] = mat_row.get('e33_C_m2', 0)
                        self.stack_info.at[idx, 'eps33'] = mat_row.get('eps33_F_m', 0)
                print(f"  Overridden {layer_name}: {params}")
            else:
                print(f"  Warning: Layer {layer_name} not found in stack")
    
    def load_stack_csv(self, material_file: str, stack_file: str):
        """Load stack from CSV files (original method)"""
        df_mpara = pd.read_csv(material_file, encoding='utf-8-sig')
        df_stack = pd.read_csv(stack_file, encoding='utf-8-sig')
        self.stack_info = self._assemble_stack(df_stack, df_mpara)
        self._print_stack()
    
    def _assemble_stack(self, df_stack: pd.DataFrame, df_mpara: pd.DataFrame) -> pd.DataFrame:
        """Assemble stack from dataframes"""
        data = {'Layer_Name': [], 'Terminal': [], 'THK': [],
                'Material': [], 'rho': [], 'c33': [], 'e33': [], 'eps33': []}
        
        for idx in range(df_stack.shape[0]):
            data['Layer_Name'].append(df_stack['Layer_Name'].iloc[idx])
            data['Terminal'].append(df_stack['Terminal'].iloc[idx])
            data['THK'].append(df_stack['THK_nm'].iloc[idx])
            data['Material'].append(df_stack['Material'].iloc[idx])
            
            q_mech = df_stack['Q_Mech'].iloc[idx]
            q_die = df_stack['Q_Die'].iloc[idx]
            Q_Mech = np.inf if q_mech == -99 else q_mech
            Q_Die = np.inf if q_die == -99 else q_die
            
            mat_name = df_stack['Material'].iloc[idx]
            rho_header = f"{mat_name}_rho"
            c33_header = f"{mat_name}_c33"
            e33_header = f"{mat_name}_e33"
            eps33_header = f"{mat_name}_eps33"
            
            data['rho'].append(df_mpara[rho_header].iloc[0])
            data['c33'].append(df_mpara[c33_header].iloc[0] * (1 + 1j/Q_Mech))
            
            try:
                data['eps33'].append(df_mpara[eps33_header].iloc[0] * (1 - 1j/Q_Die))
            except:
                data['eps33'].append(0)
            
            try:
                data['e33'].append(df_mpara[e33_header].iloc[0])
            except:
                data['e33'].append(0)
        
        stack_info = pd.DataFrame(data)
        return stack_info[stack_info.THK != 0].reset_index(drop=True)
    
    def _print_stack(self):
        """Print stack configuration"""
        print(f"\nStack configuration ({len(self.stack_info)} layers):")
        term_map = {0: "GND", 1: "BOT", 2: "TOP"}
        for _, row in self.stack_info.iterrows():
            term = term_map.get(row['Terminal'], f"T{row['Terminal']}")
            print(f"  {row['Layer_Name']:6s}: {row['Material']:6s} {row['THK']:5.0f}nm [{term}]")
    
    def simulate(self, area_um2: float, f_start: float = 1e9, f_stop: float = 3e9,
                 f_step: float = 0.1e6, rs: float = 0.0,
                 output_file: Optional[str] = None) -> Dict:
        """Run simulation"""
        if self.stack_info is None:
            raise ValueError("Stack not configured")
        
        Area = area_um2 / 1e12
        f = np.arange(f_start, f_stop, f_step)
        w = 2 * np.pi * f
        
        print(f"\nSimulation:")
        print(f"  Area: {area_um2} um^2")
        print(f"  Frequency: {f_start/1e9:.2f} - {f_stop/1e9:.2f} GHz")
        print(f"  Points: {len(f)}")
        
        import time
        start = time.perf_counter()
        z11, C0 = mason_fbar(self.stack_info, Area, w, rs)
        end = time.perf_counter()
        
        print(f"  Time: {end-start:.3f}s")
        print(f"  C0: {C0:.4e} F")
        
        self.frequency = f
        self.impedance = z11
        self.C0 = C0
        
        results = {'frequency': f, 'impedance': z11, 'C0': C0, 'area': Area}
        
        if SKRF_AVAILABLE:
            net = rf.Network(frequency=f, z=z11, f_unit='Hz')
            s11_mag = np.abs(net.s[:, 0, 0])
            fr_idx = np.argmin(s11_mag)
            fa_idx = np.argmax(s11_mag)
            
            fr, fa = f[fr_idx], f[fa_idx]
            kt2 = (np.pi/2) * (fr/fa) * (1/np.tan(np.pi/2 * fr/fa))
            
            results.update({'network': net, 'fr': fr, 'fa': fa, 'kt2': kt2})
            print(f"  fr: {fr/1e9:.4f} GHz")
            print(f"  fa: {fa/1e9:.4f} GHz")
            print(f"  kt2: {kt2:.4f}")
            
            if output_file:
                net.write_touchstone(output_file)
                print(f"  S1P saved: {output_file}")
                results['output_file'] = output_file
        
        self.results = results
        
        if output_file and SKRF_AVAILABLE:
            self._plot_results(output_file.replace('.s1p', '_plot.png'))
        
        return results
    
    def _plot_results(self, plot_file: str):
        """Generate plot"""
        if not SKRF_AVAILABLE:
            return
        
        f, z11 = self.frequency, self.impedance
        net = self.results['network']
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        s11_db = 20 * np.log10(np.abs(net.s[:, 0, 0]))
        axes[0, 0].plot(f/1e9, s11_db)
        axes[0, 0].set_title('|S11| (dB)')
        axes[0, 0].set_xlabel('Frequency (GHz)')
        axes[0, 0].grid(True, alpha=0.3)
        
        axes[0, 1].plot(f/1e9, np.angle(net.s[:, 0, 0], deg=True))
        axes[0, 1].set_title('S11 Phase (deg)')
        axes[0, 1].set_xlabel('Frequency (GHz)')
        axes[0, 1].grid(True, alpha=0.3)
        
        axes[1, 0].plot(f/1e9, np.real(z11))
        axes[1, 0].set_title('Re(Z11) (Ω)')
        axes[1, 0].set_xlabel('Frequency (GHz)')
        axes[1, 0].grid(True, alpha=0.3)
        
        axes[1, 1].plot(f/1e9, np.imag(z11))
        axes[1, 1].set_title('Im(Z11) (Ω)')
        axes[1, 1].set_xlabel('Frequency (GHz)')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(plot_file, dpi=150)
        print(f"  Plot saved: {plot_file}")
        plt.close()
    
    def get_results(self) -> Dict:
        return self.results


def main():
    parser = argparse.ArgumentParser(description='BAW S1P Generator')
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--template', choices=list(DEFAULT_STACKS.keys()),
                           help='Use default stack template')
    input_group.add_argument('--material', '-m', help='Material CSV file')
    
    parser.add_argument('--stack', '-s', help='Stack CSV file (with --material)')
    parser.add_argument('--override', help='JSON string of layer overrides')
    parser.add_argument('--area', '-a', type=float, required=True, help='Area (μm²)')
    parser.add_argument('--fstart', type=float, default=1e9, help='Start freq (Hz)')
    parser.add_argument('--fstop', type=float, default=3e9, help='Stop freq (Hz)')
    parser.add_argument('--fstep', type=float, default=0.1e6, help='Step (Hz)')
    parser.add_argument('--rs', type=float, default=0.0, help='Series R (Ω)')
    parser.add_argument('--output', '-o', help='Output S1P file')
    parser.add_argument('--material-lib', help='Material library Excel')
    
    args = parser.parse_args()
    
    gen = MasonS1PGenerator()
    gen.load_material_library(args.material_lib)
    
    if args.template:
        overrides = json.loads(args.override) if args.override else None
        gen.use_template(args.template, overrides)
    elif args.material:
        if not args.stack:
            parser.error('--stack required with --material')
        gen.load_stack_csv(args.material, args.stack)
    
    gen.simulate(area_um2=args.area, f_start=args.fstart, f_stop=args.fstop,
                f_step=args.fstep, rs=args.rs, output_file=args.output)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
