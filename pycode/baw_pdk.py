"""
BAW PDK (Process Design Kit) - Mason Model Interface

Simplified interface for BAW resonator design with ML (Mass Loading) control.
Default stack: PS/TE/PZ/BE/SD with optional ML on top electrode.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

# Import Mason model from baw-mason-s1p skill
import sys
mason_skill_path = r"C:\Users\jinhao.dai\AppData\Roaming\npm\node_modules\openclaw-cn\skills\baw-mason-s1p\scripts"
if mason_skill_path not in sys.path:
    sys.path.append(mason_skill_path)

from mason_s1p import MasonS1PGenerator, load_material_library


class BAWPDK:
    """
    BAW Process Design Kit
    
    Simplified interface for generating BAW resonator S-parameters
    with Mass Loading (ML) control for frequency tuning.
    """
    
    # Default PDK parameters
    DEFAULT_STACK = 'standard_fbar'
    DEFAULT_ML_MATERIAL = 'Mo'
    DEFAULT_AREA_UM2 = 10000
    DEFAULT_ML_THICKNESS_NM = 0  # No ML by default
    
    # Frequency sweep range
    FREQ_START = 1e9  # 1 GHz
    FREQ_STOP = 3e9   # 3 GHz
    FREQ_STEP = 0.1e6 # 0.1 MHz
    
    def __init__(self, material_lib_path: Optional[str] = None):
        """
        Initialize PDK
        
        Args:
            material_lib_path: Path to material library Excel file
        """
        self.gen = MasonS1PGenerator()
        self.gen.load_material_library(material_lib_path)
        self.material_lib = load_material_library(material_lib_path)
        
        # Current configuration
        self.ml_thickness = self.DEFAULT_ML_THICKNESS_NM
        self.area_um2 = self.DEFAULT_AREA_UM2
        self.ml_material = self.DEFAULT_ML_MATERIAL
        
        # Last simulation results
        self.last_result = None
        
    def configure(self, 
                  area_um2: Optional[float] = None,
                  ml_thickness_nm: Optional[float] = None,
                  ml_material: Optional[str] = None):
        """
        Configure PDK parameters
        
        Args:
            area_um2: Resonator area in um²
            ml_thickness_nm: Mass loading thickness in nm (0 for no ML)
            ml_material: ML material (default: Mo)
        """
        if area_um2 is not None:
            self.area_um2 = area_um2
        if ml_thickness_nm is not None:
            self.ml_thickness = ml_thickness_nm
        if ml_material is not None:
            self.ml_material = ml_material
            
        print(f"PDK Configuration:")
        print(f"  Area: {self.area_um2} um²")
        print(f"  ML: {self.ml_thickness} nm {self.ml_material}")
        
    def _build_stack_with_ml(self) -> Dict:
        """
        Build layer overrides with ML
        
        Returns:
            Layer override dictionary for mason_s1p
        """
        overrides = {}
        
        if self.ml_thickness > 0:
            # Add ML as additional layer on top of TE
            # TE thickness becomes TE + ML
            # For simplicity, we increase TE thickness
            # In real PDK, ML might be a separate layer
            te_original_thk = 240  # nm (from standard_fbar)
            te_new_thk = te_original_thk + self.ml_thickness
            overrides['TE'] = {
                'thk_nm': te_new_thk,
                'material': self.ml_material if self.ml_thickness > 50 else 'Mo'
            }
            print(f"  Stack: TE adjusted to {te_new_thk}nm")
        
        return overrides
    
    def simulate(self, 
                 output_file: Optional[str] = None,
                 f_start: float = None,
                 f_stop: float = None,
                 f_step: float = None) -> Dict:
        """
        Run simulation with current configuration
        
        Args:
            output_file: Path to save S1P file
            f_start: Start frequency (Hz)
            f_stop: Stop frequency (Hz)
            f_step: Frequency step (Hz)
        
        Returns:
            Simulation results dictionary
        """
        # Build stack with ML
        overrides = self._build_stack_with_ml()
        
        # Use template
        self.gen.use_template(self.DEFAULT_STACK, overrides)
        
        # Set default frequencies if not provided
        f_start = f_start or self.FREQ_START
        f_stop = f_stop or self.FREQ_STOP
        f_step = f_step or self.FREQ_STEP
        
        # Run simulation
        results = self.gen.simulate(
            area_um2=self.area_um2,
            f_start=f_start,
            f_stop=f_stop,
            f_step=f_step,
            output_file=output_file
        )
        
        self.last_result = results
        return results
    
    def find_ml_for_frequency(self, 
                             target_fs_hz: float,
                             ml_range_nm: Tuple[float, float] = (0, 500),
                             tolerance_hz: float = 1e6,
                             output_file: Optional[str] = None) -> Dict:
        """
        Find ML thickness for target series resonant frequency
        
        Args:
            target_fs_hz: Target series resonant frequency (Hz)
            ml_range_nm: (min, max) ML thickness to search (nm)
            tolerance_hz: Frequency matching tolerance (Hz)
            output_file: Path to save final S1P file
        
        Returns:
            Dictionary with optimal ML thickness and results
        """
        print(f"\nSearching ML for fs = {target_fs_hz/1e9:.4f} GHz")
        print(f"ML range: {ml_range_nm[0]} - {ml_range_nm[1]} nm")
        
        ml_min, ml_max = ml_range_nm
        best_ml = ml_min
        best_error = float('inf')
        best_result = None
        
        # Binary search for optimal ML
        iterations = 0
        max_iter = 20
        
        while iterations < max_iter:
            ml_mid = (ml_min + ml_max) / 2
            self.ml_thickness = ml_mid
            
            # Simulate without saving file
            result = self.simulate()
            fs = result['fr']
            error = abs(fs - target_fs_hz)
            
            print(f"  Iter {iterations+1}: ML={ml_mid:.1f}nm, fs={fs/1e9:.4f}GHz, error={error/1e6:.2f}MHz")
            
            if error < best_error:
                best_error = error
                best_ml = ml_mid
                best_result = result
            
            if error < tolerance_hz:
                print(f"  ✓ Converged! ML = {ml_mid:.1f} nm")
                break
            
            # Adjust search range
            if fs > target_fs_hz:
                # fs too high, need more ML
                ml_min = ml_mid
            else:
                # fs too low, need less ML
                ml_max = ml_mid
            
            iterations += 1
        
        # Final simulation with best ML
        self.ml_thickness = best_ml
        if output_file:
            best_result = self.simulate(output_file=output_file)
        
        return {
            'optimal_ml_nm': best_ml,
            'achieved_fs_hz': best_result['fr'],
            'error_hz': best_error,
            'result': best_result
        }
    
    def batch_simulate(self,
                      ml_thicknesses: List[float],
                      areas: Optional[List[float]] = None,
                      output_dir: Optional[str] = None) -> List[Dict]:
        """
        Batch simulation for multiple ML and Area combinations
        
        Args:
            ml_thicknesses: List of ML thicknesses (nm)
            areas: List of areas (um²), default: [10000]
            output_dir: Directory to save S1P files
        
        Returns:
            List of results for each combination
        """
        if areas is None:
            areas = [self.DEFAULT_AREA_UM2]
        
        results = []
        total = len(ml_thicknesses) * len(areas)
        count = 0
        
        print(f"\nBatch Simulation: {len(ml_thicknesses)} ML × {len(areas)} Area = {total} runs")
        
        for area in areas:
            for ml in ml_thicknesses:
                count += 1
                print(f"\n[{count}/{total}] Area={area}um², ML={ml}nm")
                
                self.configure(area_um2=area, ml_thickness_nm=ml)
                
                output_file = None
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(
                        output_dir, 
                        f"pdk_area{area}_ml{ml}.s1p"
                    )
                
                result = self.simulate(output_file=output_file)
                
                summary = {
                    'area_um2': area,
                    'ml_nm': ml,
                    'fs_ghz': result['fr'] / 1e9,
                    'fp_ghz': result['fa'] / 1e9,
                    'kt2': result['kt2'],
                    'c0_pf': result['C0'] * 1e12
                }
                results.append(summary)
        
        # Create summary DataFrame
        df = pd.DataFrame(results)
        if output_dir:
            summary_file = os.path.join(output_dir, 'batch_summary.csv')
            df.to_csv(summary_file, index=False)
            print(f"\nBatch summary saved: {summary_file}")
        
        print("\nBatch Results:")
        print(df.to_string(index=False))
        
        return results
    
    def generate_pdk_library(self,
                           fs_range_ghz: Tuple[float, float],
                           fs_step_mhz: float = 50,
                           area_um2: Optional[float] = None,
                           output_dir: str = None) -> pd.DataFrame:
        """
        Generate PDK library with uniform frequency spacing
        
        Args:
            fs_range_ghz: (min, max) series resonant frequency (GHz)
            fs_step_mhz: Frequency step (MHz)
            area_um2: Fixed area (default: use configured area)
            output_dir: Directory to save S1P files
        
        Returns:
            DataFrame with PDK library entries
        """
        if area_um2:
            self.area_um2 = area_um2
        
        fs_start, fs_stop = fs_range_ghz
        n_points = int((fs_stop - fs_start) * 1000 / fs_step_mhz) + 1
        target_freqs = np.linspace(fs_start, fs_stop, n_points)
        
        print(f"\nGenerating PDK Library:")
        print(f"  Frequency range: {fs_start} - {fs_stop} GHz")
        print(f"  Step: {fs_step_mhz} MHz")
        print(f"  Area: {self.area_um2} um²")
        print(f"  Total points: {len(target_freqs)}")
        
        library = []
        
        for i, fs in enumerate(target_freqs):
            print(f"\n[{i+1}/{len(target_freqs)}] Target fs = {fs:.3f} GHz")
            
            output_file = None
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(
                    output_dir,
                    f"pdk_fs{fs:.3f}GHz_area{self.area_um2}.s1p"
                )
            
            result = self.find_ml_for_frequency(
                target_fs_hz=fs * 1e9,
                output_file=output_file
            )
            
            entry = {
                'target_fs_ghz': fs,
                'ml_nm': result['optimal_ml_nm'],
                'achieved_fs_ghz': result['achieved_fs_hz'] / 1e9,
                'error_mhz': result['error_hz'] / 1e6,
                'kt2': result['result']['kt2'],
                'c0_pf': result['result']['C0'] * 1e12,
                'area_um2': self.area_um2
            }
            library.append(entry)
        
        df = pd.DataFrame(library)
        
        if output_dir:
            lib_file = os.path.join(output_dir, 'pdk_library.csv')
            df.to_csv(lib_file, index=False)
            print(f"\nPDK library saved: {lib_file}")
        
        print("\nPDK Library Summary:")
        print(df.to_string(index=False))
        
        return df
    
    def get_last_result(self) -> Optional[Dict]:
        """Get last simulation result"""
        return self.last_result


def main():
    """Command line interface for BAW PDK"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BAW PDK - Mason Model Interface')
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Simulate command
    sim_parser = subparsers.add_parser('simulate', help='Single simulation')
    sim_parser.add_argument('--area', type=float, default=10000, help='Area (um²)')
    sim_parser.add_argument('--ml', type=float, default=0, help='ML thickness (nm)')
    sim_parser.add_argument('--output', '-o', help='Output S1P file')
    
    # Find ML command
    find_parser = subparsers.add_parser('find-ml', help='Find ML for target frequency')
    find_parser.add_argument('--target-fs', type=float, required=True, help='Target fs (GHz)')
    find_parser.add_argument('--area', type=float, default=10000, help='Area (um²)')
    find_parser.add_argument('--output', '-o', help='Output S1P file')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch simulation')
    batch_parser.add_argument('--ml-list', required=True, help='ML list (JSON array)')
    batch_parser.add_argument('--area-list', help='Area list (JSON array)')
    batch_parser.add_argument('--output-dir', '-d', required=True, help='Output directory')
    
    # PDK library command
    lib_parser = subparsers.add_parser('library', help='Generate PDK library')
    lib_parser.add_argument('--fs-start', type=float, required=True, help='Start fs (GHz)')
    lib_parser.add_argument('--fs-stop', type=float, required=True, help='Stop fs (GHz)')
    lib_parser.add_argument('--fs-step', type=float, default=50, help='Step (MHz)')
    lib_parser.add_argument('--area', type=float, default=10000, help='Area (um²)')
    lib_parser.add_argument('--output-dir', '-d', required=True, help='Output directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize PDK
    pdk = BAWPDK()
    
    if args.command == 'simulate':
        pdk.configure(area_um2=args.area, ml_thickness_nm=args.ml)
        result = pdk.simulate(output_file=args.output)
        print(f"\nResults:")
        print(f"  fs: {result['fr']/1e9:.4f} GHz")
        print(f"  fp: {result['fa']/1e9:.4f} GHz")
        print(f"  kt2: {result['kt2']:.4f}")
        
    elif args.command == 'find-ml':
        result = pdk.find_ml_for_frequency(
            target_fs_hz=args.target_fs * 1e9,
            output_file=args.output
        )
        print(f"\nOptimal ML: {result['optimal_ml_nm']:.1f} nm")
        print(f"Achieved fs: {result['achieved_fs_hz']/1e9:.4f} GHz")
        
    elif args.command == 'batch':
        ml_list = json.loads(args.ml_list)
        area_list = json.loads(args.area_list) if args.area_list else None
        pdk.batch_simulate(ml_list, area_list, args.output_dir)
        
    elif args.command == 'library':
        pdk.generate_pdk_library(
            fs_range_ghz=(args.fs_start, args.fs_stop),
            fs_step_mhz=args.fs_step,
            area_um2=args.area,
            output_dir=args.output_dir
        )
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
