"""
Vehicle definitions and creation logic for the 2D RTS unit pipeline.
This module contains all the 3D geometry creation functions for different vehicle types.
"""

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Dict, Any, List
import trimesh


# ---------- Basic geometry helpers ----------
def box(w, h, d):
    """Create a centered box with given dimensions"""
    return trimesh.creation.box(extents=[w, h, d])


def cylinder(r, h, axis='z'):
    """Create a cylinder with given radius and height along specified axis"""
    m = trimesh.creation.cylinder(radius=r, height=h, sections=24)
    if axis == 'x': 
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, [0,1,0]))
    if axis == 'y': 
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, [1,0,0]))
    return m


def chamfered_hull(L=3.0, W=2.0, H=0.8, nose=0.8):
    """Create a hull with chamfered nose"""
    # base
    hull = box(L, W, H)
    # bevel nose by subtracting wedge
    wedge = box(nose*2, W*1.2, H*2)
    wedge.apply_translation([L/2 - nose/2, 0, 0])  # move to front
    try:
        hull = hull.difference(wedge)
    except:
        # If boolean operation fails, return original hull
        pass
    return hull


# ---------- Multi-color vehicle support ----------
@dataclass
class ColoredVehicleParts:
    """Container for vehicle parts with different colors.

    For 3D export the parts are split into groups that a game engine can
    animate independently:
      - primary_parts   : hull body (user-selected colour)
      - secondary_parts : ALL detail parts (grey) – used for 2D rendering
      - turret_parts    : turret base (subset of secondary, rotates to aim)
      - barrel_parts    : gun barrel + muzzle brake (recoils on firing)
      - mobility_parts  : wheels or treads (spin / scroll with movement)
    """
    primary_parts: List[trimesh.Trimesh]
    secondary_parts: List[trimesh.Trimesh]
    turret_parts: List[trimesh.Trimesh] = None
    barrel_parts: List[trimesh.Trimesh] = None
    mobility_parts: List[trimesh.Trimesh] = None

    def __post_init__(self):
        if self.turret_parts is None:
            self.turret_parts = []
        if self.barrel_parts is None:
            self.barrel_parts = []
        if self.mobility_parts is None:
            self.mobility_parts = []

    # ---- combined helpers (used by 2D rendering) ----
    def get_combined_mesh(self) -> trimesh.Trimesh:
        all_parts = self.primary_parts + self.secondary_parts
        return trimesh.util.concatenate(all_parts)

    # ---- per-group helpers (used by 3D export) ----
    def _exclude(self, *groups):
        excluded = set()
        for g in groups:
            excluded.update(id(p) for p in g)
        return excluded

    def get_hull_mesh(self) -> trimesh.Trimesh:
        """Body + any secondary parts that aren't turret/barrel/mobility."""
        excluded = self._exclude(self.turret_parts, self.barrel_parts, self.mobility_parts)
        hull = self.primary_parts + [p for p in self.secondary_parts if id(p) not in excluded]
        return trimesh.util.concatenate(hull) if hull else None

    def get_turret_mesh(self) -> trimesh.Trimesh:
        return trimesh.util.concatenate(self.turret_parts) if self.turret_parts else None

    def get_barrel_mesh(self) -> trimesh.Trimesh:
        return trimesh.util.concatenate(self.barrel_parts) if self.barrel_parts else None

    def get_mobility_mesh(self) -> trimesh.Trimesh:
        return trimesh.util.concatenate(self.mobility_parts) if self.mobility_parts else None

    def get_secondary_hull_parts(self) -> List[trimesh.Trimesh]:
        """Secondary parts that are NOT in any animated group."""
        excluded = self._exclude(self.turret_parts, self.barrel_parts, self.mobility_parts)
        return [p for p in self.secondary_parts if id(p) not in excluded]


# ---------- Vehicle base class ----------
@dataclass
class VehicleParameters:
    """Base parameters for all vehicles"""
    seed: int = 0
    scale_factor: float = 4.0  # 4x bigger for better detail
    

class VehicleBuilder(ABC):
    """Abstract base class for vehicle builders"""
    
    def build(self, params: VehicleParameters) -> trimesh.Trimesh:
        """Build and return the vehicle mesh (for backward compatibility)"""
        colored_parts = self.build_colored(params)
        return colored_parts.get_combined_mesh()
    
    @abstractmethod
    def build_colored(self, params: VehicleParameters) -> ColoredVehicleParts:
        """Build and return the vehicle with separated colored parts"""
        pass
    
    @abstractmethod
    def get_metadata(self, params: VehicleParameters) -> Dict[str, Any]:
        """Get vehicle-specific metadata (pivot points, muzzle positions, etc.)"""
        pass
    
    @property
    @abstractmethod
    def vehicle_type(self) -> str:
        """Return the vehicle type identifier"""
        pass


# ---------- Tank builder ----------
@dataclass
class TankParameters(VehicleParameters):
    """Parameters specific to tank generation"""
    include_treads: bool = True
    hull_length_range: Tuple[float, float] = (2.6, 3.4)
    hull_width_range: Tuple[float, float] = (1.8, 2.2)
    hull_height_range: Tuple[float, float] = (0.7, 1.0)
    turret_radius_range: Tuple[float, float] = (0.35, 0.55)
    turret_height_range: Tuple[float, float] = (0.25, 0.4)
    barrel_radius_range: Tuple[float, float] = (0.07, 0.10)
    barrel_length_range: Tuple[float, float] = (0.9, 1.3)


class TankBuilder(VehicleBuilder):
    """Builder for tank-type vehicles"""
    
    @property
    def vehicle_type(self) -> str:
        return "tank"
    
    def build_colored(self, params: TankParameters) -> ColoredVehicleParts:
        """Create a procedural tank with separated colors"""
        rnd = random.Random(params.seed)
        
        # Scale all dimensions
        L = rnd.uniform(*params.hull_length_range) * params.scale_factor
        W = rnd.uniform(*params.hull_width_range) * params.scale_factor
        H = rnd.uniform(*params.hull_height_range) * params.scale_factor
        
        # Calculate tread height for vehicle height adjustment
        tread_h = 0.4 * params.scale_factor if params.include_treads else 0
        
        # PRIMARY PARTS (user-selected color)
        primary_parts = []
        
        # Create main hull (primary color) - raised by tread height
        body = box(L, W, H)
        body.apply_translation([0, 0, tread_h/2])  # Raise hull so tread bottoms touch ground
        primary_parts.append(body)
        
        # SECONDARY PARTS (grey)
        secondary_parts = []
        
        # Create turret (secondary color) - also raised
        tr = rnd.uniform(*params.turret_radius_range) * params.scale_factor
        th = rnd.uniform(*params.turret_height_range) * params.scale_factor
        turret = cylinder(tr, th, axis='z')
        turret.apply_translation([0, 0, H/2 + th/2 + tread_h/2])  # Also raised
        secondary_parts.append(turret)
        
        # Create barrel (secondary color)
        br = rnd.uniform(*params.barrel_radius_range) * params.scale_factor
        bl = rnd.uniform(*params.barrel_length_range) * params.scale_factor
        barrel = cylinder(br, bl, axis='x')
        
        # Position barrel properly - also raised
        turret_center_z = H/2 + th/2 + tread_h/2
        barrel_start_x = tr * 0.8
        barrel.apply_translation([barrel_start_x + bl/2, 0, turret_center_z])
        secondary_parts.append(barrel)
        
        # Part groups for 3D export
        turret_group = [turret]
        barrel_group = [barrel]
        mobility_group = []

        if params.include_treads:
            tw = 0.3 * params.scale_factor
            tread_len = L * 0.9

            treadL = box(tread_len, tw, tread_h)
            treadR = box(tread_len, tw, tread_h)

            track_y_offset = W/2 + tw/2 * 0.7
            track_z_offset = 0

            treadL.apply_translation([0, track_y_offset, track_z_offset])
            treadR.apply_translation([0, -track_y_offset, track_z_offset])
            secondary_parts.extend([treadL, treadR])
            mobility_group.extend([treadL, treadR])

        return ColoredVehicleParts(
            primary_parts, secondary_parts,
            turret_parts=turret_group,
            barrel_parts=barrel_group,
            mobility_parts=mobility_group,
        )
    
    def get_metadata(self, params: TankParameters) -> Dict[str, Any]:
        """Get tank-specific metadata including 3D attachment points"""
        rnd = random.Random(params.seed)
        sf = params.scale_factor
        H = rnd.uniform(*params.hull_height_range) * sf
        tread_h = 0.4 * sf if params.include_treads else 0
        tr = rnd.uniform(*params.turret_radius_range) * sf
        th = rnd.uniform(*params.turret_height_range) * sf

        turret_mount_z = H / 2 + tread_h / 2          # top of hull
        barrel_mount_z = H / 2 + th / 2 + tread_h / 2 # centre of turret
        barrel_mount_x = tr * 0.8                      # front edge of turret

        return {
            "pivot": [0.5, 0.75],
            "muzzle": [0.6, 0.5],
            "type": "tank",
            "has_turret": True,
            "can_rotate_turret": True,
            "attachments": {
                "turret_mount": [0.0, 0.0, turret_mount_z],
                "barrel_mount": [barrel_mount_x, 0.0, barrel_mount_z],
            },
        }


# ---------- APC builder ----------
@dataclass
class APCParameters(VehicleParameters):
    """Parameters specific to APC generation"""
    include_wheels: bool = True
    hull_length_range: Tuple[float, float] = (3.0, 4.0)
    hull_width_range: Tuple[float, float] = (2.0, 2.5)
    hull_height_range: Tuple[float, float] = (1.2, 1.6)
    wheel_radius_range: Tuple[float, float] = (0.3, 0.4)
    num_wheels_per_side: int = 3


class APCBuilder(VehicleBuilder):
    """Builder for APC (Armored Personnel Carrier) vehicles"""
    
    @property
    def vehicle_type(self) -> str:
        return "apc"
    
    def build_colored(self, params: APCParameters) -> ColoredVehicleParts:
        """Create a procedural APC with separated colors"""
        rnd = random.Random(params.seed)
        
        # Scale all dimensions
        L = rnd.uniform(*params.hull_length_range) * params.scale_factor
        W = rnd.uniform(*params.hull_width_range) * params.scale_factor
        H = rnd.uniform(*params.hull_height_range) * params.scale_factor
        
        # Calculate wheel radius for vehicle height adjustment
        wr = rnd.uniform(*params.wheel_radius_range) * params.scale_factor if params.include_wheels else 0
        
        # PRIMARY PARTS (user-selected color)
        primary_parts = []
        
        # Create main hull (primary color) - raised by wheel radius
        body = box(L, W, H)
        body.apply_translation([0, 0, wr])  # Raise hull so wheel bottoms touch ground
        primary_parts.append(body)
        
        # SECONDARY PARTS (grey)
        secondary_parts = []
        
        # Create a small turret/weapon mount (secondary color) - also raised
        tr = 0.25 * params.scale_factor
        th = 0.15 * params.scale_factor
        turret = cylinder(tr, th, axis='z')
        turret.apply_translation([L*0.2, 0, H/2 + th/2 + wr])  # Offset towards front + raised
        secondary_parts.append(turret)
        
        # Small weapon (machine gun) (secondary color) - also raised
        br = 0.03 * params.scale_factor
        bl = 0.4 * params.scale_factor
        weapon = cylinder(br, bl, axis='x')
        weapon.apply_translation([L*0.2 + tr*0.8 + bl/2, 0, H/2 + th/2 + wr])  # Also raised
        secondary_parts.append(weapon)
        
        # Part groups for 3D export
        turret_group = [turret]
        barrel_group = [weapon]
        mobility_group = []

        # Add wheels if requested (secondary color)
        if params.include_wheels:
            wheel_spacing = L / (params.num_wheels_per_side + 1)

            for i in range(params.num_wheels_per_side):
                x_pos = -L/2 + wheel_spacing * (i + 1)
                z_pos = 0

                wheelL = cylinder(wr, 0.2 * params.scale_factor, axis='y')
                wheelL.apply_translation([x_pos, W/2 + 0.1 * params.scale_factor, z_pos])

                wheelR = cylinder(wr, 0.2 * params.scale_factor, axis='y')
                wheelR.apply_translation([x_pos, -W/2 - 0.1 * params.scale_factor, z_pos])

                secondary_parts.extend([wheelL, wheelR])
                mobility_group.extend([wheelL, wheelR])

        return ColoredVehicleParts(
            primary_parts, secondary_parts,
            turret_parts=turret_group,
            barrel_parts=barrel_group,
            mobility_parts=mobility_group,
        )
    
    def get_metadata(self, params: APCParameters) -> Dict[str, Any]:
        """Get APC-specific metadata including 3D attachment points"""
        rnd = random.Random(params.seed)
        sf = params.scale_factor
        L = rnd.uniform(*params.hull_length_range) * sf
        H = rnd.uniform(*params.hull_height_range) * sf
        wr = rnd.uniform(*params.wheel_radius_range) * sf if params.include_wheels else 0
        tr = 0.25 * sf
        th = 0.15 * sf

        turret_mount_z = H / 2 + wr
        barrel_mount_x = L * 0.2 + tr * 0.8
        barrel_mount_z = H / 2 + th / 2 + wr

        return {
            "pivot": [0.5, 0.7],
            "muzzle": [0.65, 0.5],
            "type": "apc",
            "has_turret": True,
            "can_rotate_turret": False,
            "transport_capacity": 8,
            "attachments": {
                "turret_mount": [L * 0.2, 0.0, turret_mount_z],
                "barrel_mount": [barrel_mount_x, 0.0, barrel_mount_z],
            },
        }


# ---------- Artillery builder ----------
@dataclass
class ArtilleryParameters(VehicleParameters):
    """Parameters specific to artillery generation"""
    include_treads: bool = True
    hull_length_range: Tuple[float, float] = (2.8, 3.6)
    hull_width_range: Tuple[float, float] = (2.2, 2.8)
    hull_height_range: Tuple[float, float] = (0.8, 1.2)
    gun_length_range: Tuple[float, float] = (2.8, 3.6)  # Longer barrel
    gun_radius_range: Tuple[float, float] = (0.18, 0.25)  # Thicker barrel


class ArtilleryBuilder(VehicleBuilder):
    """Builder for self-propelled artillery vehicles"""
    
    @property
    def vehicle_type(self) -> str:
        return "artillery"
    
    def build_colored(self, params: ArtilleryParameters) -> ColoredVehicleParts:
        """Create a procedural artillery vehicle with separated colors"""
        rnd = random.Random(params.seed)
        
        # Scale all dimensions
        L = rnd.uniform(*params.hull_length_range) * params.scale_factor
        W = rnd.uniform(*params.hull_width_range) * params.scale_factor
        H = rnd.uniform(*params.hull_height_range) * params.scale_factor
        
        # Calculate tread height for vehicle height adjustment
        tread_h = 0.5 * params.scale_factor if params.include_treads else 0
        
        # PRIMARY PARTS (user-selected color)
        primary_parts = []
        
        # Create main hull (primary color) - raised by tread height
        body = box(L, W, H)
        body.apply_translation([0, 0, tread_h/2])  # Raise hull so tread bottoms touch ground
        primary_parts.append(body)
        
        # SECONDARY PARTS (grey)
        secondary_parts = []
        
        # Create gun mount (secondary color) - also raised
        mount_r = 0.5 * params.scale_factor  # Larger mount
        mount_h = 0.4 * params.scale_factor  # Taller mount
        gun_mount = cylinder(mount_r, mount_h, axis='z')
        gun_mount.apply_translation([0, 0, H/2 + mount_h/2 + tread_h/2])  # Also raised
        secondary_parts.append(gun_mount)
        
        # Create gun support structure (secondary color) - also raised
        support_w = 0.3 * params.scale_factor
        support_h = 0.2 * params.scale_factor
        support_l = 0.8 * params.scale_factor
        gun_support = box(support_l, support_w, support_h)
        gun_support.apply_translation([mount_r * 0.6, 0, H/2 + mount_h + support_h/2 + tread_h/2])  # Also raised
        secondary_parts.append(gun_support)
        
        # Create gun cradle (secondary color)
        cradle_w = 0.4 * params.scale_factor
        cradle_h = 0.35 * params.scale_factor
        cradle_l = 0.6 * params.scale_factor
        gun_cradle = box(cradle_l, cradle_w, cradle_h)
        
        # Position gun at slight upward angle
        gun_elevation = math.radians(12)  # 12 degree elevation
        gun_z = H/2 + mount_h + support_h/2 + tread_h/2  # Also raised
        
        # Position cradle at the end of the support structure
        cradle_x = mount_r * 0.8 + support_l/2 + cradle_l/2 * 0.3
        gun_cradle.apply_transform(trimesh.transformations.rotation_matrix(gun_elevation, [0, 1, 0]))
        gun_cradle.apply_translation([cradle_x, 0, gun_z + cradle_l/2 * math.sin(gun_elevation)])
        secondary_parts.append(gun_cradle)
        
        # Create large gun barrel (secondary color)
        gun_r = rnd.uniform(*params.gun_radius_range) * params.scale_factor
        gun_l = rnd.uniform(*params.gun_length_range) * params.scale_factor
        gun_barrel = cylinder(gun_r, gun_l, axis='x')
        
        # Create muzzle brake (secondary color)
        muzzle_r = gun_r * 1.3
        muzzle_l = 0.3 * params.scale_factor
        muzzle_brake = cylinder(muzzle_r, muzzle_l, axis='x')
        
        # Position barrel threading through the cradle
        gun_start_x = cradle_x - cradle_l/4  # Start barrel slightly inside cradle
        gun_x = gun_start_x + gun_l/2 * math.cos(gun_elevation)
        gun_z_offset = gun_l/2 * math.sin(gun_elevation)
        
        # Apply rotation and translation to barrel
        gun_barrel.apply_transform(trimesh.transformations.rotation_matrix(gun_elevation, [0, 1, 0]))
        gun_barrel.apply_translation([gun_x, 0, gun_z + gun_z_offset])
        secondary_parts.append(gun_barrel)
        
        # Position muzzle brake at end of barrel
        muzzle_x = gun_start_x + gun_l * math.cos(gun_elevation)
        muzzle_z_offset = gun_l * math.sin(gun_elevation)
        muzzle_brake.apply_transform(trimesh.transformations.rotation_matrix(gun_elevation, [0, 1, 0]))
        muzzle_brake.apply_translation([muzzle_x, 0, gun_z + muzzle_z_offset])
        secondary_parts.append(muzzle_brake)
        
        # Part groups for 3D export
        turret_group = [gun_mount, gun_support, gun_cradle]
        barrel_group = [gun_barrel, muzzle_brake]
        mobility_group = []

        # Add treads (secondary color)
        if params.include_treads:
            tw = 0.4 * params.scale_factor
            tread_len = L * 0.95

            treadL = box(tread_len, tw, tread_h)
            treadR = box(tread_len, tw, tread_h)

            track_y_offset = W/2 + tw/2 * 0.6
            track_z_offset = 0

            treadL.apply_translation([0, track_y_offset, track_z_offset])
            treadR.apply_translation([0, -track_y_offset, track_z_offset])
            secondary_parts.extend([treadL, treadR])
            mobility_group.extend([treadL, treadR])

        return ColoredVehicleParts(
            primary_parts, secondary_parts,
            turret_parts=turret_group,
            barrel_parts=barrel_group,
            mobility_parts=mobility_group,
        )
    
    def get_metadata(self, params: ArtilleryParameters) -> Dict[str, Any]:
        """Get artillery-specific metadata including 3D attachment points"""
        rnd = random.Random(params.seed)
        sf = params.scale_factor
        H = rnd.uniform(*params.hull_height_range) * sf
        tread_h = 0.5 * sf if params.include_treads else 0
        mount_r = 0.5 * sf
        mount_h = 0.4 * sf
        support_h = 0.2 * sf
        support_l = 0.8 * sf

        turret_mount_z = H / 2 + tread_h / 2
        barrel_mount_x = mount_r * 0.8 + support_l / 2
        barrel_mount_z = H / 2 + mount_h + support_h / 2 + tread_h / 2

        return {
            "pivot": [0.5, 0.75],
            "muzzle": [0.8, 0.55],
            "type": "artillery",
            "has_turret": True,
            "can_rotate_turret": True,
            "range": "long",
            "damage": "high",
            "attachments": {
                "turret_mount": [0.0, 0.0, turret_mount_z],
                "barrel_mount": [barrel_mount_x, 0.0, barrel_mount_z],
            },
        }


# ---------- Vehicle factory ----------
class VehicleFactory:
    """Factory for creating vehicles of different types"""
    
    def __init__(self):
        self._builders = {
            "tank": TankBuilder(),
            "apc": APCBuilder(),
            "artillery": ArtilleryBuilder()
        }
    
    def register_builder(self, vehicle_type: str, builder: VehicleBuilder):
        """Register a new vehicle builder"""
        self._builders[vehicle_type] = builder
    
    def get_available_types(self) -> list:
        """Get list of available vehicle types"""
        return list(self._builders.keys())
    
    def create_vehicle(self, vehicle_type: str, params: VehicleParameters) -> trimesh.Trimesh:
        """Create a vehicle of the specified type"""
        if vehicle_type not in self._builders:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")
        
        builder = self._builders[vehicle_type]
        return builder.build(params)
    
    def get_vehicle_metadata(self, vehicle_type: str, params: VehicleParameters) -> Dict[str, Any]:
        """Get metadata for a vehicle type"""
        if vehicle_type not in self._builders:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")
        
        builder = self._builders[vehicle_type]
        return builder.get_metadata(params)


# ---------- Convenience functions ----------
def create_tank(seed=0, include_treads=True) -> trimesh.Trimesh:
    """Convenience function to create a tank (backward compatibility)"""
    factory = VehicleFactory()
    params = TankParameters(seed=seed, include_treads=include_treads)
    return factory.create_vehicle("tank", params)


def create_apc(seed=0, include_wheels=True) -> trimesh.Trimesh:
    """Convenience function to create an APC"""
    factory = VehicleFactory()
    params = APCParameters(seed=seed, include_wheels=include_wheels)
    return factory.create_vehicle("apc", params)


def create_artillery(seed=0, include_treads=True) -> trimesh.Trimesh:
    """Convenience function to create artillery"""
    factory = VehicleFactory()
    params = ArtilleryParameters(seed=seed, include_treads=include_treads)
    return factory.create_vehicle("artillery", params)
