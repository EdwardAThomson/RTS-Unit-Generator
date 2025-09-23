"""
Main vehicle pipeline for the 2D RTS unit system.
This module orchestrates vehicle creation and rendering using the modular components.
"""

import os
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any

from vehicle_definitions import (
    VehicleFactory, VehicleParameters, 
    TankParameters, APCParameters, ArtilleryParameters
)
from rendering_engine import VehicleRenderer, VehicleExporter, RenderConfig


# ---------- Pipeline configuration ----------
@dataclass
class VehicleSpec:
    """Specification for a vehicle to be generated"""
    name: str
    vehicle_type: str  # "tank", "apc", "artillery"
    seed: int
    color: Tuple[int, int, int]  # RGB primary color (for main hull)
    n_dirs: int = 8
    cell: int = 512
    generate_debug: bool = True
    
    # Secondary color for details (turrets, barrels, etc.)
    secondary_color: Tuple[int, int, int] = (160, 160, 160)  # Light grey default
    
    # Vehicle-specific parameters (optional)
    custom_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_params is None:
            self.custom_params = {}


class VehiclePipeline:
    """Main pipeline for generating vehicles"""
    
    def __init__(self, render_config: RenderConfig = None):
        self.factory = VehicleFactory()
        self.exporter = VehicleExporter(VehicleRenderer(render_config))
    
    def create_vehicle_parameters(self, spec: VehicleSpec) -> VehicleParameters:
        """Create appropriate parameters object based on vehicle type"""
        base_params = {
            "seed": spec.seed,
            "scale_factor": 4.0,  # Keep 4x scale for detail
            **spec.custom_params
        }
        
        if spec.vehicle_type == "tank":
            return TankParameters(**base_params)
        elif spec.vehicle_type == "apc":
            return APCParameters(**base_params)
        elif spec.vehicle_type == "artillery":
            return ArtilleryParameters(**base_params)
        else:
            raise ValueError(f"Unknown vehicle type: {spec.vehicle_type}")
    
    def generate_vehicle(self, spec: VehicleSpec, out_root="out/vehicles") -> Dict[str, Any]:
        """Generate a single vehicle with all assets"""
        print(f"Generating {spec.vehicle_type}: {spec.name}")
        
        # Create vehicle parameters
        params = self.create_vehicle_parameters(spec)
        
        # Generate colored vehicle parts
        builder = self.factory._builders[spec.vehicle_type]
        colored_parts = builder.build_colored(params)
        
        # Generate combined mesh for backward compatibility
        mesh = colored_parts.get_combined_mesh()
        
        # Get vehicle metadata
        vehicle_metadata = self.factory.get_vehicle_metadata(spec.vehicle_type, params)
        
        # Export vehicle with two-color system
        result = self.exporter.export_vehicle(
            mesh=mesh,
            name=spec.name,
            vehicle_type=spec.vehicle_type,
            color=spec.color,
            vehicle_metadata=vehicle_metadata,
            out_root=out_root,
            n_dirs=spec.n_dirs,
            cell=spec.cell,
            generate_debug=spec.generate_debug,
            secondary_color=spec.secondary_color,
            colored_parts=colored_parts
        )
        
        print(f"✓ Generated {spec.name} -> {result['sprite_sheet']}")
        return result
    
    def generate_batch(self, specs: List[VehicleSpec], out_root="out/vehicles") -> List[Dict[str, Any]]:
        """Generate multiple vehicles in batch"""
        results = []
        
        print(f"Starting batch generation of {len(specs)} vehicles...")
        for i, spec in enumerate(specs, 1):
            print(f"[{i}/{len(specs)}] ", end="")
            result = self.generate_vehicle(spec, out_root)
            results.append(result)
        
        print(f"\n✓ Batch complete! Generated {len(results)} vehicles.")
        print(f"Check {out_root}/ for sprite sheets and metadata.")
        
        return results
    
    def get_available_vehicle_types(self) -> List[str]:
        """Get list of available vehicle types"""
        return self.factory.get_available_types()


# ---------- Preset configurations ----------
class PresetConfigurations:
    """Predefined vehicle configurations for common use cases"""
    
    @staticmethod
    def create_faction_vehicles(faction_name: str, faction_color: Tuple[int, int, int], 
                               base_seed: int = 100) -> List[VehicleSpec]:
        """Create a standard set of vehicles for a faction"""
        vehicles = []
        
        # Main battle tank
        vehicles.append(VehicleSpec(
            name=f"{faction_name.title()} Main Battle Tank",
            vehicle_type="tank",
            seed=base_seed,
            color=faction_color
        ))
        
        # Heavy tank variant
        vehicles.append(VehicleSpec(
            name=f"{faction_name.title()} Heavy Tank",
            vehicle_type="tank",
            seed=base_seed + 50,
            color=faction_color,
            custom_params={
                "hull_length_range": (3.2, 3.8),
                "hull_width_range": (2.4, 2.8),
                "turret_radius_range": (0.5, 0.65),
                "barrel_length_range": (1.2, 1.6)
            }
        ))
        
        # APC
        vehicles.append(VehicleSpec(
            name=f"{faction_name.title()} APC",
            vehicle_type="apc",
            seed=base_seed + 100,
            color=faction_color
        ))
        
        # Artillery
        vehicles.append(VehicleSpec(
            name=f"{faction_name.title()} Artillery",
            vehicle_type="artillery",
            seed=base_seed + 200,
            color=faction_color
        ))
        
        return vehicles
    
    @staticmethod
    def create_demo_batch() -> List[VehicleSpec]:
        """Create a demonstration batch with various vehicles"""
        specs = []
        
        # Standard vehicle types (no faction colors)
        default_color = (180, 180, 180)  # Lighter neutral gray
        
        # Main Battle Tank
        specs.append(VehicleSpec(
            name="Main Battle Tank",
            vehicle_type="tank",
            seed=100,
            color=default_color
        ))
        
        # Heavy Tank (was Light Tank - now the bigger one)
        specs.append(VehicleSpec(
            name="Heavy Tank",
            vehicle_type="tank",
            seed=150,
            color=default_color,
            custom_params={
                "hull_length_range": (3.2, 3.8),
                "hull_width_range": (2.4, 2.8),
                "turret_radius_range": (0.5, 0.65),
                "barrel_length_range": (1.2, 1.6)
            }
        ))
        
        # Light Tank (was Heavy Tank - now the smaller one)
        specs.append(VehicleSpec(
            name="Light Tank",
            vehicle_type="tank",
            seed=200,
            color=default_color,
            custom_params={
                "hull_length_range": (2.2, 2.8),
                "hull_width_range": (1.6, 1.9),
                "turret_radius_range": (0.3, 0.45)
            }
        ))
        
        # APC
        specs.append(VehicleSpec(
            name="Armored Personnel Carrier",
            vehicle_type="apc",
            seed=300,
            color=default_color
        ))
        
        # Artillery
        specs.append(VehicleSpec(
            name="Self Propelled Artillery",
            vehicle_type="artillery",
            seed=400,
            color=default_color
        ))
        
        return specs


# ---------- Main execution ----------
def main():
    """Main function for command-line usage"""
    # Create pipeline
    pipeline = VehiclePipeline()
    
    # Generate demo batch
    demo_specs = PresetConfigurations.create_demo_batch()
    
    # Run generation
    results = pipeline.generate_batch(demo_specs)
    
    # Print summary
    print(f"\n=== Generation Summary ===")
    print(f"Total vehicles generated: {len(results)}")
    print(f"Vehicle types: {set(spec.vehicle_type for spec in demo_specs)}")
    print(f"Output directory: out/vehicles/")
    
    return results


if __name__ == "__main__":
    main()
