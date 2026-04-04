"""
Rendering engine for the 2D RTS unit pipeline.
This module handles all 3D to 2D rendering, sprite sheet generation, and export functionality.
"""

import os
import json
import math
from typing import List, Tuple, Dict, Any
import numpy as np
import trimesh
import pyrender
from PIL import Image

# Import the ColoredVehicleParts class
from vehicle_definitions import ColoredVehicleParts


# ---------- Rendering configuration ----------
class RenderConfig:
    """Configuration for rendering parameters"""
    
    def __init__(self):
        # Camera settings
        self.elevation_deg = 35.264  # Isometric angle
        self.camera_distance = 20.0
        self.camera_y_offset = -10.5  # Centers tank body properly
        self.ortho_mag = 22.0  # Guaranteed no clipping
        
        # Lighting
        self.light_intensity = 4.0
        self.light_position = [8, 8, 20]
        
        # Rendering
        self.background_color = [0.01, 0.01, 0.01, 0.0]  # Very dark but not transparent
        self.znear = 0.1
        self.zfar = 50.0


# ---------- Utility functions ----------
def to_unit_bbox(mesh: trimesh.Trimesh, target_size=2.0) -> trimesh.Trimesh:
    """Scale mesh to fit within unit bounding box"""
    m = mesh.copy()
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(
            g for g in m.dump().geometries if isinstance(g, trimesh.Trimesh)
        ))
    bbox = m.bounds
    center = (bbox[0] + bbox[1]) / 2.0
    m.apply_translation(-center)
    extents = (bbox[1] - bbox[0])
    scale = target_size / float(extents.max() if extents.max() > 0 else 1.0)
    m.apply_scale(scale)
    return m


def trimesh_to_pyrender(mesh: trimesh.Trimesh, rgba=(0.65, 0.68, 0.72, 1.0)) -> pyrender.Mesh:
    """Convert trimesh to pyrender mesh with material"""
    mat = pyrender.MetallicRoughnessMaterial(
        baseColorFactor=rgba, metallicFactor=0.0, roughnessFactor=1.0
    )
    return pyrender.Mesh.from_trimesh(mesh, material=mat, smooth=False)


def look_at(eye, target=(0, 0, 0), up=(0, 0, 1)) -> np.ndarray:
    """Create a view matrix that looks from eye to target"""
    eye = np.array(eye, dtype=np.float32)
    target = np.array(target, dtype=np.float32)
    up = np.array(up, dtype=np.float32)
    
    # Forward vector (from eye to target)
    forward = target - eye
    forward = forward / np.linalg.norm(forward)
    
    # Right vector
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    
    # Up vector (recompute to ensure orthogonality)
    up = np.cross(right, forward)
    
    # Create view matrix
    view_matrix = np.eye(4, dtype=np.float32)
    view_matrix[0, :3] = right
    view_matrix[1, :3] = up
    view_matrix[2, :3] = -forward  # Negative because we're looking down -Z
    view_matrix[:3, 3] = [-np.dot(right, eye), -np.dot(up, eye), np.dot(forward, eye)]
    
    return view_matrix


def iso_eye(elev_deg=35.264, azim_deg=45.0, radius=6.0) -> Tuple[float, float, float]:
    """Calculate isometric camera position"""
    e = math.radians(elev_deg)
    a = math.radians(azim_deg)
    x = radius * math.cos(e) * math.cos(a)
    y = radius * math.cos(e) * math.sin(a)
    z = radius * math.sin(e)
    return (x, y, z)


def srgb_to_lin(c):
    """Convert sRGB color (0-255) to linear (0-1)"""
    x = c / 255.0
    return math.pow(x, 2.2)


def color_to_rgba(color_rgb: Tuple[int, int, int], a=1.0):
    """Convert RGB color tuple to RGBA with linear color space"""
    r, g, b = color_rgb
    return (srgb_to_lin(r), srgb_to_lin(g), srgb_to_lin(b), a)


# ---------- Main rendering class ----------
class VehicleRenderer:
    """Main class for rendering vehicles to sprite sheets"""
    
    def __init__(self, config: RenderConfig = None):
        self.config = config or RenderConfig()
    
    def render_directions(self, mesh: trimesh.Trimesh, out_dir: str, basename: str,
                         n_dirs=8, img_size=512, base_rgba=(0.65, 0.68, 0.72, 1.0)) -> List[str]:
        """Render vehicle from multiple directions"""
        os.makedirs(out_dir, exist_ok=True)
        
        # Keep the mesh at its original size (4x bigger for better detail)
        m = mesh.copy()
        
        paths = []
        for i in range(n_dirs):
            # Calculate rotation for this direction
            az = (360.0 / n_dirs) * i
            az_rad = math.radians(az)
            
            # Rotate mesh for this direction
            rotation_matrix = trimesh.transformations.rotation_matrix(az_rad, [0, 0, 1])
            rotated_mesh = m.copy()
            rotated_mesh.apply_transform(rotation_matrix)
            
            # Create material
            material = pyrender.MetallicRoughnessMaterial(
                baseColorFactor=base_rgba,
                metallicFactor=0.0,
                roughnessFactor=1.0
            )
            
            # Convert to pyrender mesh
            pr_mesh = pyrender.Mesh.from_trimesh(rotated_mesh, material=material)
            
            # Create scene
            scene = pyrender.Scene(bg_color=self.config.background_color)
            scene.add(pr_mesh)
            
            # Add lighting
            light = pyrender.DirectionalLight(intensity=self.config.light_intensity)
            light_pose = np.array([
                [1, 0, 0, self.config.light_position[0]],
                [0, 1, 0, self.config.light_position[1]],
                [0, 0, 1, self.config.light_position[2]],
                [0, 0, 0, 1]
            ])
            scene.add(light, pose=light_pose)
            
            # Add camera
            camera = pyrender.OrthographicCamera(
                xmag=self.config.ortho_mag, 
                ymag=self.config.ortho_mag,
                znear=self.config.znear, 
                zfar=self.config.zfar
            )
            
            # Position camera
            elev_rad = math.radians(self.config.elevation_deg)
            camera_pose = np.array([
                [1, 0, 0, 0],
                [0, math.cos(elev_rad), -math.sin(elev_rad), self.config.camera_y_offset],
                [0, math.sin(elev_rad), math.cos(elev_rad), self.config.camera_distance],
                [0, 0, 0, 1]
            ])
            scene.add(camera, pose=camera_pose)
            
            # Render
            renderer = pyrender.OffscreenRenderer(img_size, img_size)
            color, depth = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
            renderer.delete()
            
            # Debug info for first frame
            if i == 0:
                non_bg_pixels = np.sum(np.any(color[:, :, :3] > [3, 3, 3], axis=2))
                print(f"✓ Rendering {basename}: {non_bg_pixels} vehicle pixels rendered")
            
            # Save frame
            fp = os.path.join(out_dir, f"{basename}_{i:02d}.png")
            Image.fromarray(color, "RGBA").save(fp)
            paths.append(fp)
        
        return paths
    
    def render_colored_directions(self, colored_parts: ColoredVehicleParts, out_dir: str, basename: str,
                                 primary_rgba: Tuple[float, float, float, float],
                                 secondary_rgba: Tuple[float, float, float, float],
                                 n_dirs=8, img_size=512) -> List[str]:
        """Render vehicle with two colors from multiple directions"""
        os.makedirs(out_dir, exist_ok=True)
        
        paths = []
        for i in range(n_dirs):
            # Calculate rotation for this direction
            az = (360.0 / n_dirs) * i
            az_rad = math.radians(az)
            rotation_matrix = trimesh.transformations.rotation_matrix(az_rad, [0, 0, 1])
            
            # Create scene
            scene = pyrender.Scene(bg_color=self.config.background_color)
            
            # Add primary parts (user-selected color)
            if colored_parts.primary_parts:
                primary_combined = trimesh.util.concatenate(colored_parts.primary_parts)
                primary_rotated = primary_combined.copy()
                primary_rotated.apply_transform(rotation_matrix)
                
                primary_material = pyrender.MetallicRoughnessMaterial(
                    baseColorFactor=primary_rgba,
                    metallicFactor=0.0,
                    roughnessFactor=1.0
                )
                primary_mesh = pyrender.Mesh.from_trimesh(primary_rotated, material=primary_material)
                scene.add(primary_mesh)
            
            # Add secondary parts (grey)
            if colored_parts.secondary_parts:
                secondary_combined = trimesh.util.concatenate(colored_parts.secondary_parts)
                secondary_rotated = secondary_combined.copy()
                secondary_rotated.apply_transform(rotation_matrix)
                
                secondary_material = pyrender.MetallicRoughnessMaterial(
                    baseColorFactor=secondary_rgba,
                    metallicFactor=0.0,
                    roughnessFactor=1.0
                )
                secondary_mesh = pyrender.Mesh.from_trimesh(secondary_rotated, material=secondary_material)
                scene.add(secondary_mesh)
            
            # Add lighting
            light = pyrender.DirectionalLight(intensity=self.config.light_intensity)
            light_pose = np.array([
                [1, 0, 0, self.config.light_position[0]],
                [0, 1, 0, self.config.light_position[1]],
                [0, 0, 1, self.config.light_position[2]],
                [0, 0, 0, 1]
            ])
            scene.add(light, pose=light_pose)
            
            # Add camera
            camera = pyrender.OrthographicCamera(
                xmag=self.config.ortho_mag,
                ymag=self.config.ortho_mag,
                znear=self.config.znear,
                zfar=self.config.zfar
            )
            
            # Position camera
            elev_rad = math.radians(self.config.elevation_deg)
            camera_pose = np.array([
                [1, 0, 0, 0],
                [0, math.cos(elev_rad), -math.sin(elev_rad), self.config.camera_y_offset],
                [0, math.sin(elev_rad), math.cos(elev_rad), self.config.camera_distance],
                [0, 0, 0, 1]
            ])
            scene.add(camera, pose=camera_pose)
            
            # Render
            renderer = pyrender.OffscreenRenderer(img_size, img_size)
            color, depth = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
            renderer.delete()
            
            # Debug info for first frame
            if i == 0:
                non_bg_pixels = np.sum(np.any(color[:, :, :3] > [3, 3, 3], axis=2))
                print(f"✓ Rendering {basename}: {non_bg_pixels} vehicle pixels rendered")
            
            # Save frame
            fp = os.path.join(out_dir, f"{basename}_{i:02d}.png")
            Image.fromarray(color, "RGBA").save(fp)
            paths.append(fp)
        
        return paths
    
    def _add_coordinate_axes(self, scene: pyrender.Scene, rotation_matrix: np.ndarray, axis_length: float = 8.0):
        """Add coordinate axes to the scene for reference (X=red, Y=green, Z=blue)"""
        # Create axes as visible cylinders (scaled for vehicle size)
        axis_radius = 0.2
        
        # Position axes offset from vehicle center to avoid overlap
        axis_offset = [-6.0, -6.0, -3.0]  # Offset in X, Y, Z
        
        # X-axis (red) - points in +X direction
        x_axis = trimesh.creation.cylinder(radius=axis_radius, height=axis_length)
        # Rotate to align with X-axis (default cylinder is along Z)
        x_axis.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, [0, 1, 0]))
        x_axis.apply_translation([axis_offset[0] + axis_length/2, axis_offset[1], axis_offset[2]])
        x_axis.apply_transform(rotation_matrix)
        
        x_material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=(1.0, 0.0, 0.0, 1.0),  # Red
            metallicFactor=0.0,
            roughnessFactor=1.0
        )
        x_mesh = pyrender.Mesh.from_trimesh(x_axis, material=x_material)
        scene.add(x_mesh)
        
        # Y-axis (green) - points in +Y direction  
        y_axis = trimesh.creation.cylinder(radius=axis_radius, height=axis_length)
        # Rotate to align with Y-axis
        y_axis.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/2, [1, 0, 0]))
        y_axis.apply_translation([axis_offset[0], axis_offset[1] + axis_length/2, axis_offset[2]])
        y_axis.apply_transform(rotation_matrix)
        
        y_material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=(0.0, 1.0, 0.0, 1.0),  # Green
            metallicFactor=0.0,
            roughnessFactor=1.0
        )
        y_mesh = pyrender.Mesh.from_trimesh(y_axis, material=y_material)
        scene.add(y_mesh)
        
        # Z-axis (blue) - points in +Z direction (default cylinder orientation)
        z_axis = trimesh.creation.cylinder(radius=axis_radius, height=axis_length)
        z_axis.apply_translation([axis_offset[0], axis_offset[1], axis_offset[2] + axis_length/2])
        z_axis.apply_transform(rotation_matrix)
        
        z_material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=(0.0, 0.0, 1.0, 1.0),  # Blue
            metallicFactor=0.0,
            roughnessFactor=1.0
        )
        z_mesh = pyrender.Mesh.from_trimesh(z_axis, material=z_material)
        scene.add(z_mesh)
    
    def generate_colored_debug_views(self, colored_parts: ColoredVehicleParts, out_dir: str, basename: str,
                                    primary_rgba: Tuple[float, float, float, float],
                                    secondary_rgba: Tuple[float, float, float, float],
                                    img_size=512):
        """Generate debug views with two-color rendering"""
        os.makedirs(out_dir, exist_ok=True)
        
        # Define debug camera angles: [name, elevation, azimuth, roll, description]
        debug_angles = [
            # Z-axis rotations (camera moves around vehicle horizontally, Z-height constant)
            ("z_rot_0deg", 0.0, 0.0, 0.0, "Z-rotation 0° (front view)"),
            ("z_rot_90deg", 0.0, 90.0, 0.0, "Z-rotation 90° (right side)"),
            ("z_rot_180deg", 0.0, 180.0, 0.0, "Z-rotation 180° (back view)"),
            ("z_rot_270deg", 0.0, 270.0, 0.0, "Z-rotation 270° (left side)"),
            
            # X-axis rotations (camera moves up/down, looking at vehicle center)
            ("x_rot_neg90deg", -90.0, 0.0, 0.0, "X-rotation -90° (bottom view)"),
            ("x_rot_neg45deg", -45.0, 0.0, 0.0, "X-rotation -45° (low angle)"),
            ("x_rot_0deg", 0.0, 0.0, 0.0, "X-rotation 0° (level view)"),
            ("x_rot_45deg", 45.0, 0.0, 0.0, "X-rotation 45° (high angle)"),
            ("x_rot_90deg", 90.0, 0.0, 0.0, "X-rotation 90° (top view)"),
            
            # Y-axis rotations (camera moves left/right around vehicle)
            ("y_rot_0deg", 0.0, 0.0, 0.0, "Y-rotation 0° (no roll)"),
            ("y_rot_45deg", 0.0, 0.0, 45.0, "Y-rotation 45° (tilted)"),
            ("y_rot_90deg", 0.0, 0.0, 90.0, "Y-rotation 90° (sideways)"),
            ("y_rot_270deg", 0.0, 0.0, 270.0, "Y-rotation 270° (opposite tilt)"),
        ]
        
        print(f"  Generating {len(debug_angles)} colored debug views...")
        
        for view_name, elev, azim, roll, description in debug_angles:
            # Create scene
            scene = pyrender.Scene(bg_color=self.config.background_color)
            
            # Add coordinate axes for reference (no rotation - keep at origin)
            identity_matrix = np.eye(4)
            self._add_coordinate_axes(scene, identity_matrix)
            
            # Add primary parts (user-selected color) - keep vehicle centered at origin
            if colored_parts.primary_parts:
                primary_combined = trimesh.util.concatenate(colored_parts.primary_parts)
                # Don't rotate the vehicle - keep it centered
                
                primary_material = pyrender.MetallicRoughnessMaterial(
                    baseColorFactor=primary_rgba,
                    metallicFactor=0.0,
                    roughnessFactor=1.0
                )
                primary_mesh = pyrender.Mesh.from_trimesh(primary_combined, material=primary_material)
                scene.add(primary_mesh)
            
            # Add secondary parts (grey) - keep vehicle centered at origin
            if colored_parts.secondary_parts:
                secondary_combined = trimesh.util.concatenate(colored_parts.secondary_parts)
                # Don't rotate the vehicle - keep it centered
                
                secondary_material = pyrender.MetallicRoughnessMaterial(
                    baseColorFactor=secondary_rgba,
                    metallicFactor=0.0,
                    roughnessFactor=1.0
                )
                secondary_mesh = pyrender.Mesh.from_trimesh(secondary_combined, material=secondary_material)
                scene.add(secondary_mesh)
            
            # Add lighting
            light = pyrender.DirectionalLight(intensity=self.config.light_intensity)
            light_pose = np.array([
                [1, 0, 0, self.config.light_position[0]],
                [0, 1, 0, self.config.light_position[1]],
                [0, 0, 1, self.config.light_position[2]],
                [0, 0, 0, 1]
            ])
            scene.add(light, pose=light_pose)
            
            # Add camera
            camera = pyrender.OrthographicCamera(
                xmag=self.config.ortho_mag,
                ymag=self.config.ortho_mag,
                znear=self.config.znear,
                zfar=self.config.zfar
            )
            
            # Position camera - use simpler approach that works
            elev_rad = math.radians(elev)
            azim_rad = math.radians(azim)
            roll_rad = math.radians(roll)
            
            # Simple camera positioning - start with basic elevation and azimuth
            # Apply rotations to the basic camera pose
            base_pose = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, self.config.camera_y_offset],
                [0, 0, 1, self.config.camera_distance],
                [0, 0, 0, 1]
            ])
            
            # Apply elevation rotation (X-axis)
            elev_rotation = np.array([
                [1, 0, 0, 0],
                [0, math.cos(elev_rad), -math.sin(elev_rad), 0],
                [0, math.sin(elev_rad), math.cos(elev_rad), 0],
                [0, 0, 0, 1]
            ])
            
            # Apply azimuth rotation (Z-axis) 
            azim_rotation = np.array([
                [math.cos(azim_rad), -math.sin(azim_rad), 0, 0],
                [math.sin(azim_rad), math.cos(azim_rad), 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ])
            
            # Apply roll rotation (Y-axis)
            roll_rotation = np.array([
                [math.cos(roll_rad), 0, math.sin(roll_rad), 0],
                [0, 1, 0, 0],
                [-math.sin(roll_rad), 0, math.cos(roll_rad), 0],
                [0, 0, 0, 1]
            ])
            
            # Combine rotations: roll * elevation * azimuth * base_pose
            camera_pose = roll_rotation @ elev_rotation @ azim_rotation @ base_pose
            scene.add(camera, pose=camera_pose)
            
            # Render
            renderer = pyrender.OffscreenRenderer(img_size, img_size)
            color, depth = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
            renderer.delete()
            
            # Save debug view
            fp = os.path.join(out_dir, f"{basename}_{view_name}.png")
            Image.fromarray(color, "RGBA").save(fp)
        
        print(f"  Debug views saved to: {out_dir}")
        return out_dir
    
    def generate_debug_views(self, mesh: trimesh.Trimesh, out_dir: str, basename: str,
                           img_size=512, base_rgba=(0.65, 0.68, 0.72, 1.0)):
        """Generate additional debug views for development and debugging"""
        os.makedirs(out_dir, exist_ok=True)
        
        m = mesh.copy()
        
        # Define debug camera angles: [name, elevation, azimuth, roll, description]
        debug_angles = [
            ("side_0deg", 0.0, 0.0, 0.0, "Side view - 0° rotation"),
            ("side_90deg", 0.0, 90.0, 0.0, "Side view - 90° rotation"),
            ("side_180deg", 0.0, 180.0, 0.0, "Side view - 180° rotation"),
            ("side_270deg", 0.0, 270.0, 0.0, "Side view - 270° rotation"),
            ("top_view", 90.0, 0.0, 0.0, "True top-down view"),
            ("bottom_view", -90.0, 0.0, 0.0, "Bottom view (wheels visible)"),
            ("front_view", 0.0, 0.0, 0.0, "Front view"),
            ("back_view", 0.0, 180.0, 0.0, "Back view"),
            ("left_view", 0.0, 270.0, 0.0, "Left side view"),
            ("right_view", 0.0, 90.0, 0.0, "Right side view"),
            ("iso_north", 35.264, 0.0, 0.0, "Isometric North (game angle)"),
            ("iso_east", 35.264, 90.0, 0.0, "Isometric East"),
            ("iso_south", 35.264, 180.0, 0.0, "Isometric South"),
            ("iso_west", 35.264, 270.0, 0.0, "Isometric West"),
        ]
        
        print(f"  Generating {len(debug_angles)} debug views...")
        
        for view_name, elev, azim, roll, description in debug_angles:
            # Calculate rotation for this view
            azim_rad = math.radians(azim)
            
            # Rotate mesh for this direction
            rotation_matrix = trimesh.transformations.rotation_matrix(azim_rad, [0, 0, 1])
            rotated_mesh = m.copy()
            rotated_mesh.apply_transform(rotation_matrix)
            
            # Create material
            material = pyrender.MetallicRoughnessMaterial(
                baseColorFactor=base_rgba,
                metallicFactor=0.0,
                roughnessFactor=1.0
            )
            
            # Convert to pyrender mesh
            pr_mesh = pyrender.Mesh.from_trimesh(rotated_mesh, material=material)
            
            # Create scene
            scene = pyrender.Scene(bg_color=self.config.background_color)
            
            # Add coordinate axes for reference
            self._add_coordinate_axes(scene, rotation_matrix)
            
            scene.add(pr_mesh)
            
            # Add light
            light = pyrender.DirectionalLight(intensity=self.config.light_intensity)
            light_pose = np.array([
                [1, 0, 0, self.config.light_position[0]],
                [0, 1, 0, self.config.light_position[1]],
                [0, 0, 1, self.config.light_position[2]],
                [0, 0, 0, 1]
            ])
            scene.add(light, pose=light_pose)
            
            # Add camera with debug angle
            camera = pyrender.OrthographicCamera(
                xmag=self.config.ortho_mag,
                ymag=self.config.ortho_mag,
                znear=self.config.znear,
                zfar=self.config.zfar
            )
            
            elev_rad = math.radians(elev)
            camera_pose = np.array([
                [1, 0, 0, 0],
                [0, math.cos(elev_rad), -math.sin(elev_rad), self.config.camera_y_offset],
                [0, math.sin(elev_rad), math.cos(elev_rad), self.config.camera_distance],
                [0, 0, 0, 1]
            ])
            scene.add(camera, pose=camera_pose)
            
            # Render
            renderer = pyrender.OffscreenRenderer(img_size, img_size)
            color, depth = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
            renderer.delete()
            
            # Save debug view
            fp = os.path.join(out_dir, f"{basename}_{view_name}.png")
            Image.fromarray(color, "RGBA").save(fp)
        
        print(f"  Debug views saved to: {out_dir}")


# ---------- Sprite sheet generation ----------
class SpriteSheetGenerator:
    """Handles sprite sheet creation and metadata generation"""
    
    @staticmethod
    def make_sprite_sheet(frames: List[str], out_path: str, cols: int, cell: int, pad=0):
        """Create a sprite sheet from individual frame images"""
        assert len(frames) % cols == 0, "rows must be integer; adjust cols"
        rows = len(frames) // cols
        W = cols * cell + (cols - 1) * pad
        H = rows * cell + (rows - 1) * pad
        sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        
        for idx, fp in enumerate(frames):
            img = Image.open(fp).convert("RGBA")
            if img.size != (cell, cell):
                img = img.resize((cell, cell), Image.NEAREST)
            r, c = divmod(idx, cols)
            x = c * (cell + pad)
            y = r * (cell + pad)
            sheet.paste(img, (x, y), img)
        
        sheet.save(out_path)
    
    @staticmethod
    def generate_metadata(name: str, vehicle_type: str, n_dirs: int, cell: int, 
                         color: Tuple[int, int, int], vehicle_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata JSON for the sprite sheet"""
        base_meta = {
            "name": name,
            "directions": n_dirs,
            "framesPerDirection": 1,
            "frameWidth": cell,
            "frameHeight": cell,
            "order": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][:n_dirs],
            "color": color,
            "vehicle_type": vehicle_type
        }
        
        # Merge with vehicle-specific metadata
        base_meta.update(vehicle_metadata)
        return base_meta


# ---------- Export pipeline ----------
class VehicleExporter:
    """Handles the complete export pipeline for vehicles"""
    
    def __init__(self, renderer: VehicleRenderer = None, sprite_generator: SpriteSheetGenerator = None):
        self.renderer = renderer or VehicleRenderer()
        self.sprite_generator = sprite_generator or SpriteSheetGenerator()
    
    def export_3d_mesh(self, colored_parts: 'ColoredVehicleParts', name: str,
                       primary_color: tuple, secondary_color: tuple,
                       out_root: str = "out/vehicles") -> dict:
        """Export vehicle as separate GLB files for game-engine animation.

        Produces (when parts exist):
          - <name>.glb              combined mesh (for previewing)
          - <name>_hull.glb         body + any non-animated detail parts
          - <name>_turret.glb       turret base (rotates to aim)
          - <name>_barrel.glb       gun barrel (recoils on firing)
          - <name>_mobility.glb     wheels / treads (spin with movement)
        """
        mesh_dir = os.path.join(out_root, name, "meshes")
        os.makedirs(mesh_dir, exist_ok=True)

        def _apply_vertex_color(mesh_obj, color_rgb):
            r, g, b = color_rgb
            n_verts = len(mesh_obj.vertices)
            mesh_obj.visual = trimesh.visual.ColorVisuals(
                mesh=mesh_obj,
                vertex_colors=np.tile([r, g, b, 255], (n_verts, 1)).astype(np.uint8)
            )
            return mesh_obj

        def _build_colored_scene(parts_primary, parts_secondary):
            scene = trimesh.Scene()
            for i, part in enumerate(parts_primary):
                colored = _apply_vertex_color(part.copy(), primary_color)
                scene.add_geometry(colored, node_name=f"primary_{i}")
            for i, part in enumerate(parts_secondary):
                colored = _apply_vertex_color(part.copy(), secondary_color)
                scene.add_geometry(colored, node_name=f"secondary_{i}")
            return scene

        def _export_part(mesh_obj, suffix, color):
            if mesh_obj is None:
                return None
            _apply_vertex_color(mesh_obj, color)
            path = os.path.join(mesh_dir, f"{name}_{suffix}.glb")
            mesh_obj.export(path)
            return path

        result = {}

        # Combined mesh (everything, for previewing in Blender etc.)
        combined_scene = _build_colored_scene(
            colored_parts.primary_parts, colored_parts.secondary_parts
        )
        combined_path = os.path.join(mesh_dir, f"{name}.glb")
        combined_scene.export(combined_path)
        result["combined_glb"] = combined_path

        # Individual animated parts
        hull_path = _export_part(colored_parts.get_hull_mesh(), "hull", primary_color)
        if hull_path:
            result["hull_glb"] = hull_path

        turret_path = _export_part(colored_parts.get_turret_mesh(), "turret", secondary_color)
        if turret_path:
            result["turret_glb"] = turret_path

        barrel_path = _export_part(colored_parts.get_barrel_mesh(), "barrel", secondary_color)
        if barrel_path:
            result["barrel_glb"] = barrel_path

        mobility_path = _export_part(colored_parts.get_mobility_mesh(), "mobility", secondary_color)
        if mobility_path:
            result["mobility_glb"] = mobility_path

        exported = [k.replace("_glb", ".glb") for k in result]
        print(f"  3D meshes exported ({len(exported)} files): {mesh_dir}")

        return result

    def export_vehicle(self, mesh: trimesh.Trimesh, name: str, vehicle_type: str,
                      color: Tuple[int, int, int], vehicle_metadata: Dict[str, Any],
                      out_root="out/vehicles", n_dirs=8, cell=512, generate_debug=True,
                      secondary_color: Tuple[int, int, int] = None, colored_parts: ColoredVehicleParts = None,
                      export_3d: bool = False):
        """Export a complete vehicle with sprite sheet and metadata"""
        
        frames_dir = os.path.join(out_root, name, "frames")
        
        # Use two-color rendering if colored parts are provided
        if colored_parts is not None and secondary_color is not None:
            # Convert colors to RGBA
            primary_rgba = color_to_rgba(color, 1.0)
            secondary_rgba = color_to_rgba(secondary_color, 1.0)
            
            # Render with two colors
            frames = self.renderer.render_colored_directions(
                colored_parts, frames_dir, basename=name,
                primary_rgba=primary_rgba, secondary_rgba=secondary_rgba,
                n_dirs=n_dirs, img_size=cell
            )
        else:
            # Fallback to single-color rendering
            rgba = color_to_rgba(color, 1.0)
            frames = self.renderer.render_directions(
                mesh, frames_dir, basename=name,
                n_dirs=n_dirs, img_size=cell, base_rgba=rgba
            )
        
        # Generate debug views if requested
        if generate_debug:
            debug_dir = os.path.join(out_root, name, "debug_views")
            if colored_parts is not None and secondary_color is not None:
                # Use two-color debug views
                primary_rgba = color_to_rgba(color, 1.0)
                secondary_rgba = color_to_rgba(secondary_color, 1.0)
                self.renderer.generate_colored_debug_views(
                    colored_parts, debug_dir, basename=name,
                    primary_rgba=primary_rgba, secondary_rgba=secondary_rgba,
                    img_size=cell
                )
            else:
                # Fallback to single-color debug views
                debug_mesh = colored_parts.get_combined_mesh() if colored_parts else mesh
                debug_rgba = color_to_rgba(color, 1.0)
                self.renderer.generate_debug_views(
                    debug_mesh, debug_dir, basename=name,
                    img_size=cell, base_rgba=debug_rgba
                )
        
        # Create sprite sheet
        sheet_path = os.path.join(out_root, name, f"{name}_sheet.png")
        self.sprite_generator.make_sprite_sheet(frames, sheet_path, cols=n_dirs, cell=cell, pad=0)
        
        # Generate and save metadata
        metadata = self.sprite_generator.generate_metadata(
            name, vehicle_type, n_dirs, cell, color, vehicle_metadata
        )
        
        # Export 3D meshes if requested
        mesh_result = {}
        if export_3d and colored_parts is not None:
            sec_color = secondary_color if secondary_color is not None else (160, 160, 160)
            mesh_result = self.export_3d_mesh(
                colored_parts, name,
                primary_color=color,
                secondary_color=sec_color,
                out_root=out_root
            )
            metadata["meshes"] = mesh_result

        metadata_path = os.path.join(out_root, name, f"{name}.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "sprite_sheet": sheet_path,
            "metadata": metadata_path,
            "frames": frames,
            "debug_dir": debug_dir if generate_debug else None,
            **mesh_result
        }
