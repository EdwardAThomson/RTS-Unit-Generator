# RTS Unit Generator

This project generates 3D vehicle models and renders them as 2D sprite sheets for RTS games. The system has been refactored into modular components for better maintainability and extensibility.

## 🏗️ Architecture Overview

The system is now organized into several modular components:

### Core Modules

1. **`vehicle_definitions.py`** - Vehicle creation logic
   - Abstract base classes for vehicle builders
   - Specific implementations for tanks, APCs, artillery
   - Vehicle factory for creating different types
   - Parameterized vehicle generation

2. **`rendering_engine.py`** - Rendering and export logic
   - 3D to 2D rendering with PyRender
   - Two-color vehicle system (hull + detail colors)
   - Sprite sheet generation
   - Metadata export
   - Advanced debug view generation (13 axis-based views with coordinate axes)

3. **`vehicle_pipeline.py`** - Main orchestration
   - High-level pipeline for vehicle generation
   - Batch processing capabilities
   - Preset configurations
   - Command-line interface

4. **`gui_app.py`** - Graphical user interface
   - Vehicle selection and editing
   - Two-color system (hull color + detail color pickers)
   - Real-time preview
   - Batch generation with progress tracking
   - Configuration save/load

### Legacy Files

- **`multi_vehicle_pipeline.py`** - Original monolithic script (preserved for reference)

## 🚀 Quick Start

### Using the GUI Application

The easiest way to use the system is through the GUI:

```bash
# Activate virtual environment
source venv/bin/activate

# Launch GUI
python gui_app.py
```

The GUI provides:
- Vehicle list management (add, remove, duplicate)
- Vehicle editor with real-time parameter adjustment
- Preview generation
- Batch processing with progress tracking
- Preset configurations
- Configuration save/load

### Using the Command Line

For automated workflows, use the pipeline directly:

```bash
# Activate virtual environment
source venv/bin/activate

# Generate demo batch
python vehicle_pipeline.py

# Or use programmatically
python -c "
from vehicle_pipeline import VehiclePipeline, VehicleSpec
pipeline = VehiclePipeline()
spec = VehicleSpec('my_tank', 'tank', seed=123, color=(70, 110, 200))
pipeline.generate_vehicle(spec)
"
```

### Using as a Library

Import and use the modular components:

```python
from vehicle_definitions import VehicleFactory, TankParameters
from rendering_engine import VehicleExporter
from vehicle_pipeline import VehiclePipeline

# Create vehicles programmatically
factory = VehicleFactory()
params = TankParameters(seed=123, include_treads=True)
tank_mesh = factory.create_vehicle('tank', params)

# Or use the high-level pipeline
pipeline = VehiclePipeline()
spec = VehicleSpec('custom_tank', 'tank', 123, (255, 0, 0))
result = pipeline.generate_vehicle(spec)
```

## 🎮 Vehicle Types

The system supports multiple vehicle types:

### Tanks
- Main battle tanks with turrets and barrels
- Configurable hull dimensions, turret size, barrel length
- Optional treads
- Suitable for front-line combat units

### APCs (Armored Personnel Carriers)
- Troop transport vehicles
- Wheeled configuration
- Fixed weapon mounts
- Larger, more rectangular hulls

### Artillery
- Self-propelled artillery units
- Large caliber guns with elevation
- Wide, stable platforms
- Long-range support units

## 🎨 Customization

### Two-Color Vehicle System

The system supports realistic two-color rendering:

- **Hull Color**: Main body color (user-selectable)
- **Detail Color**: Mechanical parts color (turrets, barrels, wheels, treads)

```python
# Create a vehicle with custom colors
spec = VehicleSpec(
    name='Custom Tank',
    vehicle_type='tank',
    seed=123,
    color=(100, 150, 200),           # Hull color (blue)
    secondary_color=(80, 80, 80),    # Detail color (gray)
    generate_debug=True
)
```

### Debug View System

Advanced debug views help visualize vehicle geometry:

- **13 systematic views** organized by rotation axis
- **Coordinate axes** (Red=X, Green=Y, Blue=Z) in every view
- **Z-axis rotations**: Horizontal views (front, right, back, left)
- **X-axis rotations**: Vertical views (bottom to top)
- **Y-axis rotations**: Camera roll/tilt variations

### Vehicle Parameters

Each vehicle type has specific parameters you can customize:

```python
# Tank parameters
tank_params = TankParameters(
    seed=123,
    scale_factor=4.0,
    hull_length_range=(2.6, 3.4),
    hull_width_range=(1.8, 2.2),
    turret_radius_range=(0.35, 0.55),
    barrel_length_range=(0.9, 1.3),
    include_treads=True
)

# APC parameters
apc_params = APCParameters(
    seed=456,
    hull_length_range=(3.0, 4.0),
    hull_width_range=(2.0, 2.5),
    num_wheels_per_side=3,
    include_wheels=True
)
```

### Rendering Configuration

Customize the rendering pipeline:

```python
from rendering_engine import RenderConfig, VehicleRenderer

config = RenderConfig()
config.elevation_deg = 35.264  # Isometric angle
config.ortho_mag = 22.0        # Camera zoom
config.light_intensity = 4.0   # Lighting strength

renderer = VehicleRenderer(config)
```

### Adding New Vehicle Types

To add a new vehicle type:

1. Create a parameters class inheriting from `VehicleParameters`
2. Create a builder class inheriting from `VehicleBuilder`
3. Implement the `build()` and `get_metadata()` methods
4. Register with the `VehicleFactory`

```python
@dataclass
class HoverTankParameters(VehicleParameters):
    hover_height: float = 0.5
    # ... other parameters

class HoverTankBuilder(VehicleBuilder):
    @property
    def vehicle_type(self) -> str:
        return "hover_tank"
    
    def build(self, params: HoverTankParameters) -> trimesh.Trimesh:
        # Implementation here
        pass
    
    def get_metadata(self, params: HoverTankParameters) -> Dict[str, Any]:
        # Metadata here
        pass

# Register with factory
factory = VehicleFactory()
factory.register_builder("hover_tank", HoverTankBuilder())
```

## 📁 Output Structure

Generated vehicles are organized as follows:

```
out/vehicles/
├── vehicle_name/
│   ├── vehicle_name_sheet.png    # Sprite sheet
│   ├── vehicle_name.json         # Metadata
│   ├── frames/                   # Individual direction frames
│   │   ├── vehicle_name_00.png
│   │   ├── vehicle_name_01.png
│   │   └── ...
│   └── debug_views/              # Debug camera angles
│       ├── vehicle_name_top_view.png
│       ├── vehicle_name_side_0deg.png
│       └── ...
```

### Metadata Format

Each vehicle includes a JSON metadata file:

```json
{
  "name": "tank_alpha_blue",
  "directions": 8,
  "framesPerDirection": 1,
  "frameWidth": 512,
  "frameHeight": 512,
  "order": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
  "color": [70, 110, 200],
  "vehicle_type": "tank",
  "pivot": [0.5, 0.75],
  "muzzle": [0.6, 0.5],
  "type": "tank",
  "has_turret": true,
  "can_rotate_turret": true
}
```

## 🔧 Development

### Project Structure

```
RTS-Unit-Generator/
├── vehicle_definitions.py     # Vehicle creation logic
├── rendering_engine.py        # Rendering and export
├── vehicle_pipeline.py        # Main pipeline
├── gui_app.py                 # GUI application
├── requirements.txt           # Dependencies
├── README.md                  # This documentation
├── .gitignore                 # Git ignore rules
├── venv/                      # Virtual environment (not in git)
├── out/                       # Generated output (not in git)
├── temp/                      # Temporary files (not in git)
└── archive/                   # Legacy files (not in git)
```

### Dependencies

- **trimesh** - 3D geometry processing
- **pyrender** - 3D rendering
- **Pillow** - Image processing
- **numpy** - Numerical computing
- **tkinter** - GUI framework (included with Python)

### GitHub Setup

To set up this project from GitHub:

```bash
# Clone the repository
git clone https://github.com/yourusername/RTS-Unit-Generator.git
cd RTS-Unit-Generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test the installation
python gui_app.py
```

### Testing

Run the test suite:

```bash
source venv/bin/activate

# Test core functionality
python -c "
from vehicle_definitions import VehicleFactory
from vehicle_pipeline import VehiclePipeline
print('✓ All modules imported successfully')
"

# Test vehicle creation
python -c "
from vehicle_definitions import VehicleFactory, TankParameters
factory = VehicleFactory()
tank = factory.create_vehicle('tank', TankParameters(seed=123))
print('✓ Vehicle creation test passed')
"
```

## 🎯 Benefits of Refactoring

### Modularity
- Separated concerns into focused modules
- Easy to maintain and extend
- Clear interfaces between components

### Extensibility
- Simple to add new vehicle types
- Configurable rendering pipeline
- Plugin-like architecture for builders

### Usability
- GUI for non-technical users
- Command-line for automation
- Library API for integration

### Maintainability
- Clear code organization
- Comprehensive documentation
- Type hints and dataclasses

## 🚀 Future Enhancements

Potential improvements for the system:

1. **More Vehicle Types**
   - Aircraft (helicopters, jets)
   - Naval units (boats, submarines)
   - Infantry units
   - Buildings and structures

2. **Advanced Rendering**
   - Animation support
   - Particle effects
   - Multiple texture variants
   - Normal maps for lighting

3. **Enhanced GUI**
   - 3D preview window
   - Drag-and-drop vehicle editing
   - Batch operation templates
   - Export to game engines

4. **Performance Optimization**
   - Multi-threaded rendering
   - GPU acceleration
   - Caching system
   - Progressive generation

5. **Integration Features**
   - Game engine plugins
   - Asset pipeline integration
   - Version control support
   - Cloud rendering


## 📄 License

Probably MIT.