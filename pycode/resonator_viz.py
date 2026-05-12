"""
Resonator Performance Visualization Tool - Enhanced Version

Supports:
- Excel/CSV files with S-parameters
- Touchstone S1P files
- Direct numpy arrays
- Multiple visualization modes
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
from typing import Optional, Tuple, List, Union
from pathlib import Path

# Optional imports
try:
    import skrf as rf
    SKRF_AVAILABLE = True
except ImportError:
    SKRF_AVAILABLE = False

try:
    from scipy.interpolate import interp1d
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def group_delay(freq: np.ndarray, s_complex: np.ndarray) -> np.ndarray:
    """Calculate group delay from S-parameters"""
    phase = np.angle(s_complex)
    phase_unwrapped = np.unwrap(phase)
    return -np.gradient(phase_unwrapped, freq) / (2 * np.pi)


def calculate_bode_q(freq: np.ndarray, s11: np.ndarray, gd: np.ndarray) -> np.ndarray:
    """Calculate Bode Q factor"""
    s11_mag = np.abs(s11)
    denom = 1 - s11_mag**2
    denom = np.where(denom < 1e-10, 1e-10, denom)
    return 2 * np.pi * freq * gd * s11_mag / denom


def s_to_z(s11: np.ndarray, z0: float = 50.0) -> np.ndarray:
    """Convert S11 to Z11"""
    return z0 * (1 + s11) / (1 - s11)


def s_to_y(s11: np.ndarray, z0: float = 50.0) -> np.ndarray:
    """Convert S11 to Y11"""
    return (1 - s11) / (1 + s11) / z0


def db20(x: np.ndarray) -> np.ndarray:
    """Convert to dB"""
    x_safe = np.where(np.abs(x) < 1e-20, 1e-20, x)
    return 20 * np.log10(np.abs(x_safe))


class ResonatorAnalyzer:
    """Universal resonator data analyzer supporting multiple input formats"""
    
    def __init__(self):
        self.frequency = None
        self.s11 = None
        self.s11_db = None
        self.z11 = None
        self.z11_db = None
        self.y11 = None
        self.y11_db = None
        self.y11_real_db = None
        self.group_delay = None
        self.bode_q = None
        self.raw_data = None
        self.source_file = None
        self.input_format = None
    
    def load_s1p(self, filepath: str) -> 'ResonatorAnalyzer':
        """
        Load data from Touchstone S1P file
        
        Args:
            filepath: Path to .s1p file
        
        Returns:
            self for method chaining
        """
        if not SKRF_AVAILABLE:
            raise ImportError("scikit-rf required for S1P files. Install: pip install scikit-rf")
        
        print(f"Loading S1P file: {filepath}")
        network = rf.Network(filepath)
        
        self.frequency = network.f
        self.s11 = network.s[:, 0, 0]
        self.source_file = filepath
        self.input_format = 's1p'
        
        print(f"  Frequency range: {self.frequency[0]/1e9:.3f} - {self.frequency[-1]/1e9:.3f} GHz")
        print(f"  Points: {len(self.frequency)}")
        
        self._calculate_all()
        return self
    
    def load_excel(self, filepath: str, freq_column: int = 0,
                   s11_real_col: int = 1, s11_imag_col: int = 2,
                   freq_unit: str = 'Hz', sheet_name: Union[str, int] = 0) -> 'ResonatorAnalyzer':
        """
        Load data from Excel file
        
        Args:
            filepath: Path to .xlsx file
            freq_column: Column index for frequency
            s11_real_col: Column index for S11 real part
            s11_imag_col: Column index for S11 imaginary part
            freq_unit: Frequency unit ('Hz', 'kHz', 'MHz', 'GHz')
            sheet_name: Sheet name or index
        """
        print(f"Loading Excel file: {filepath}")
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        self.raw_data = df
        
        return self._process_dataframe(df, freq_column, s11_real_col, s11_imag_col, 
                                       freq_unit, filepath, 'excel')
    
    def load_csv(self, filepath: str, freq_column: int = 0,
                 s11_real_col: int = 1, s11_imag_col: int = 2,
                 freq_unit: str = 'Hz', delimiter: str = ',') -> 'ResonatorAnalyzer':
        """
        Load data from CSV file
        
        Args:
            filepath: Path to .csv file
            freq_column: Column index for frequency
            s11_real_col: Column index for S11 real part
            s11_imag_col: Column index for S11 imaginary part
            freq_unit: Frequency unit
            delimiter: CSV delimiter
        """
        print(f"Loading CSV file: {filepath}")
        df = pd.read_csv(filepath, delimiter=delimiter)
        self.raw_data = df
        
        return self._process_dataframe(df, freq_column, s11_real_col, s11_imag_col,
                                       freq_unit, filepath, 'csv')
    
    def load_data(self, filepath: str, **kwargs) -> 'ResonatorAnalyzer':
        """
        Auto-detect file type and load data
        
        Args:
            filepath: Path to data file
            **kwargs: Additional arguments for specific formats
        """
        ext = Path(filepath).suffix.lower()
        
        if ext == '.s1p':
            return self.load_s1p(filepath)
        elif ext in ['.xlsx', '.xls']:
            return self.load_excel(filepath, **kwargs)
        elif ext == '.csv':
            return self.load_csv(filepath, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def _process_dataframe(self, df: pd.DataFrame, freq_col: int, real_col: int, 
                          imag_col: int, freq_unit: str, filepath: str, 
                          fmt: str) -> 'ResonatorAnalyzer':
        """Process dataframe to extract S-parameters"""
        # Extract frequency
        self.frequency = df.iloc[:, freq_col].values
        
        # Convert frequency to Hz
        unit_mult = {'hz': 1.0, 'khz': 1e3, 'mhz': 1e6, 'ghz': 1e9}
        mult = unit_mult.get(freq_unit.lower(), 1.0)
        self.frequency = self.frequency * mult
        
        # Extract S11
        s_real = df.iloc[:, real_col].values
        s_imag = df.iloc[:, imag_col].values
        self.s11 = s_real + 1j * s_imag
        
        self.source_file = filepath
        self.input_format = fmt
        
        print(f"  Frequency range: {self.frequency[0]/1e9:.3f} - {self.frequency[-1]/1e9:.3f} GHz")
        print(f"  Points: {len(self.frequency)}")
        
        self._calculate_all()
        return self
    
    def set_data(self, frequency: np.ndarray, s11: np.ndarray) -> 'ResonatorAnalyzer':
        """
        Set data directly from arrays
        
        Args:
            frequency: Frequency array (Hz)
            s11: Complex S11 array
        """
        self.frequency = frequency
        self.s11 = s11
        self.input_format = 'array'
        self._calculate_all()
        return self
    
    def _calculate_all(self):
        """Calculate all derived parameters"""
        self.s11_db = db20(self.s11)
        self.z11 = s_to_z(self.s11)
        self.z11_db = db20(self.z11)
        self.y11 = s_to_y(self.s11)
        self.y11_db = db20(self.y11)
        self.y11_real_db = db20(np.real(self.y11))
        self.group_delay = group_delay(self.frequency, self.s11)
        self.bode_q = calculate_bode_q(self.frequency, self.s11, self.group_delay)
    
    def get_resonant_params(self) -> dict:
        """Extract resonator parameters"""
        s11_mag = np.abs(self.s11)
        fr_idx = np.argmin(s11_mag)
        fa_idx = np.argmax(s11_mag)
        
        fr = self.frequency[fr_idx]
        fa = self.frequency[fa_idx]
        
        # Calculate kt2
        kt2 = (np.pi / 2) * (fr / fa) * (1 / np.tan(np.pi / 2 * fr / fa))
        
        # Bandwidth
        bw = fa - fr
        
        # Max Q
        q_max = np.max(self.bode_q)
        q_fr = self.bode_q[fr_idx]
        
        return {
            'fr': fr,
            'fa': fa,
            'kt2': kt2,
            'bandwidth': bw,
            'q_max': q_max,
            'q_at_fr': q_fr,
            's11_min': s11_mag[fr_idx],
            's11_max': s11_mag[fa_idx]
        }
    
    def plot(self, figsize: Tuple[int, int] = (14, 10),
             plot_type: str = 'standard',
             freq_unit: str = 'GHz',
             save_path: Optional[str] = None,
             show: bool = True) -> plt.Figure:
        """
        Create visualization plot
        
        Args:
            figsize: Figure size
            plot_type: 'standard' (4 plots), 'full' (6 plots), 'simple' (2 plots)
            freq_unit: Frequency unit for display
            save_path: Optional path to save figure
            show: Whether to show the plot
        
        Returns:
            Matplotlib figure
        """
        # Frequency conversion for plotting
        unit_mult = {'hz': 1.0, 'khz': 1e-3, 'mhz': 1e-6, 'ghz': 1e-9}
        mult = unit_mult.get(freq_unit.lower(), 1e-9)
        freq_plot = self.frequency * mult
        
        if plot_type == 'simple':
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            axes = axes.reshape(1, 2)
        elif plot_type == 'full':
            fig, axes = plt.subplots(3, 2, figsize=(12, 14))
        else:  # standard
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Common plot settings
        xlabel = f'Frequency ({freq_unit})'
        
        # Plot 1: S11 magnitude
        axes[0, 0].plot(freq_plot, self.s11_db, 'b-', linewidth=1)
        axes[0, 0].set_title('|S11| (dB)', fontsize=11, fontweight='bold')
        axes[0, 0].set_ylabel('S11 (dB)')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=-3, color='r', linestyle='--', alpha=0.5, label='-3dB')
        axes[0, 0].legend()
        
        # Plot 2: Q factor
        # Limit Q to reasonable range for visualization
        q_plot = np.clip(self.bode_q, 0, np.percentile(self.bode_q, 95) * 2)
        axes[0, 1].plot(freq_plot, q_plot, 'g-', linewidth=1)
        axes[0, 1].set_title('Q Factor (Bode)', fontsize=11, fontweight='bold')
        axes[0, 1].set_ylabel('Q')
        axes[0, 1].grid(True, alpha=0.3)
        
        if plot_type == 'simple':
            axes[1, 0].set_xlabel(xlabel)
            axes[1, 1].set_xlabel(xlabel)
        else:
            # Plot 3: Y11 magnitude
            axes[1, 0].plot(freq_plot, self.y11_db, 'r-', linewidth=1)
            axes[1, 0].set_title('|Y11| (dB)', fontsize=11, fontweight='bold')
            axes[1, 0].set_ylabel('Y11 (dB)')
            axes[1, 0].set_xlabel(xlabel)
            axes[1, 0].grid(True, alpha=0.3)
            
            # Plot 4: Real part of Y11
            axes[1, 1].plot(freq_plot, self.y11_real_db, 'm-', linewidth=1)
            axes[1, 1].set_title('Re(Y11) (dB)', fontsize=11, fontweight='bold')
            axes[1, 1].set_ylabel('Re(Y11) (dB)')
            axes[1, 1].set_xlabel(xlabel)
            axes[1, 1].grid(True, alpha=0.3)
        
        if plot_type == 'full':
            # Plot 5: Group delay
            gd_ns = self.group_delay * 1e9  # Convert to ns
            axes[2, 0].plot(freq_plot, gd_ns, 'c-', linewidth=1)
            axes[2, 0].set_title('Group Delay', fontsize=11, fontweight='bold')
            axes[2, 0].set_ylabel('Group Delay (ns)')
            axes[2, 0].set_xlabel(xlabel)
            axes[2, 0].grid(True, alpha=0.3)
            
            # Plot 6: Smith chart (if skrf available)
            if SKRF_AVAILABLE:
                try:
                    from skrf.plotting import smith
                    smith(ax=axes[2, 1], chart_type='z')
                    # Plot S11 on Smith chart
                    re = np.real(self.s11)
                    im = np.imag(self.s11)
                    axes[2, 1].plot(re, im, 'b-', linewidth=1, alpha=0.7)
                    axes[2, 1].set_title('Smith Chart', fontsize=11, fontweight='bold')
                except:
                    axes[2, 1].text(0.5, 0.5, 'Smith chart\nnot available', 
                                   ha='center', va='center', transform=axes[2, 1].transAxes)
                    axes[2, 1].set_title('Smith Chart')
            else:
                axes[2, 1].text(0.5, 0.5, 'scikit-rf required\nfor Smith chart',
                               ha='center', va='center', transform=axes[2, 1].transAxes)
                axes[2, 1].set_title('Smith Chart')
        
        plt.tight_layout()
        
        # Add source info
        if self.source_file:
            fig.text(0.5, 0.02, f'Source: {os.path.basename(self.source_file)}', 
                    ha='center', fontsize=9, style='italic')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved: {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def save_results(self, filepath: str):
        """Save analysis results to CSV"""
        results = pd.DataFrame({
            'Frequency_Hz': self.frequency,
            'S11_Real': np.real(self.s11),
            'S11_Imag': np.imag(self.s11),
            'S11_dB': self.s11_db,
            'Z11_dB': self.z11_db,
            'Y11_dB': self.y11_db,
            'Y11_Real_dB': self.y11_real_db,
            'GroupDelay_s': self.group_delay,
            'Q_Bode': self.bode_q
        })
        results.to_csv(filepath, index=False)
        print(f"Results saved: {filepath}")


def main():
    parser = argparse.ArgumentParser(description='Resonator Performance Visualization')
    parser.add_argument('--input', '-i', required=True, 
                       help='Input file (S1P, Excel, or CSV)')
    parser.add_argument('--output', '-o', help='Output plot file')
    parser.add_argument('--export', '-e', help='Export results to CSV')
    parser.add_argument('--plot-type', default='standard',
                       choices=['simple', 'standard', 'full'],
                       help='Plot complexity')
    parser.add_argument('--freq-unit', default='GHz',
                       choices=['Hz', 'kHz', 'MHz', 'GHz'],
                       help='Frequency unit in input file')
    parser.add_argument('--display-unit', default='GHz',
                       choices=['Hz', 'kHz', 'MHz', 'GHz'],
                       help='Frequency unit for display')
    parser.add_argument('--freq-col', type=int, default=0,
                       help='Frequency column (Excel/CSV)')
    parser.add_argument('--real-col', type=int, default=1,
                       help='S11 real column (Excel/CSV)')
    parser.add_argument('--imag-col', type=int, default=2,
                       help='S11 imag column (Excel/CSV)')
    parser.add_argument('--sheet', default=0,
                       help='Sheet name/index (Excel)')
    parser.add_argument('--no-show', action='store_true',
                       help='Do not display plot (save only)')
    
    args = parser.parse_args()
    
    # Check input file
    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        return 1
    
    # Create analyzer
    analyzer = ResonatorAnalyzer()
    
    # Load data based on file extension
    ext = Path(args.input).suffix.lower()
    
    try:
        if ext == '.s1p':
            analyzer.load_s1p(args.input)
        elif ext in ['.xlsx', '.xls']:
            sheet = int(args.sheet) if args.sheet.isdigit() else args.sheet
            analyzer.load_excel(args.input, 
                              freq_column=args.freq_col,
                              s11_real_col=args.real_col,
                              s11_imag_col=args.imag_col,
                              freq_unit=args.freq_unit,
                              sheet_name=sheet)
        elif ext == '.csv':
            analyzer.load_csv(args.input,
                            freq_column=args.freq_col,
                            s11_real_col=args.real_col,
                            s11_imag_col=args.imag_col,
                            freq_unit=args.freq_unit)
        else:
            print(f"Error: Unsupported file format: {ext}")
            return 1
    except Exception as e:
        print(f"Error loading file: {e}")
        return 1
    
    # Get resonator parameters
    params = analyzer.get_resonant_params()
    print("\nResonator Parameters:")
    print(f"  fr: {params['fr']/1e9:.4f} GHz")
    print(f"  fa: {params['fa']/1e9:.4f} GHz")
    print(f"  kt²: {params['kt2']:.4f} ({params['kt2']*100:.2f}%)")
    print(f"  Bandwidth: {params['bandwidth']/1e6:.2f} MHz")
    print(f"  Q (max): {params['q_max']:.1f}")
    print(f"  Q (at fr): {params['q_at_fr']:.1f}")
    
    # Generate plot
    analyzer.plot(
        plot_type=args.plot_type,
        freq_unit=args.display_unit,
        save_path=args.output,
        show=not args.no_show
    )
    
    # Export results if requested
    if args.export:
        analyzer.save_results(args.export)
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
