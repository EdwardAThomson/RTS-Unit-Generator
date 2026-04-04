"""
GUI application for the 2D RTS vehicle pipeline.
Provides an easy-to-use interface for selecting and generating vehicles.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import threading
import os
import json
from typing import Dict, List, Tuple, Any
from PIL import Image, ImageTk

from vehicle_pipeline import VehiclePipeline, VehicleSpec, PresetConfigurations
from vehicle_definitions import VehicleFactory


class VehicleGeneratorGUI:
    """Main GUI application for vehicle generation"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("2D RTS Vehicle Generator")
        self.root.geometry("1000x700")
        
        # Initialize pipeline
        self.pipeline = VehiclePipeline()
        self.factory = VehicleFactory()
        
        # GUI state
        self.vehicle_specs = []
        self.current_preview = None
        self.generation_thread = None
        
        # Setup GUI
        self.setup_gui()
        
        # Load some default vehicles
        self.load_demo_vehicles()
    
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Create main frames
        self.create_menu()
        self.create_main_frames()  # This now creates the status bar first
        self.create_vehicle_list()
        self.create_vehicle_editor()
        self.create_preview_panel()
        self.create_generation_panel()
    
    def create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Preset", command=self.load_preset)
        file_menu.add_command(label="Save Configuration", command=self.save_configuration)
        file_menu.add_command(label="Load Configuration", command=self.load_configuration)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_main_frames(self):
        """Create the main layout frames"""
        # Create status bar first to reserve bottom space
        self.create_status_bar()
        
        # Main content frame (everything above status bar)
        self.main_content_frame = ttk.Frame(self.root)
        self.main_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for vehicle list and editor
        self.left_frame = ttk.Frame(self.main_content_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # Right panel for preview and generation
        self.right_frame = ttk.Frame(self.main_content_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    def create_vehicle_list(self):
        """Create the vehicle list panel"""
        # Vehicle list frame
        list_frame = ttk.LabelFrame(self.left_frame, text="Vehicle List")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.vehicle_listbox = tk.Listbox(list_container, width=30)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.vehicle_listbox.yview)
        self.vehicle_listbox.config(yscrollcommand=scrollbar.set)
        
        self.vehicle_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.vehicle_listbox.bind('<<ListboxSelect>>', self.on_vehicle_select)
        
        # Buttons
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Add Vehicle", command=self.add_vehicle).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Remove", command=self.remove_vehicle).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Duplicate", command=self.duplicate_vehicle).pack(side=tk.LEFT)
    
    def create_vehicle_editor(self):
        """Create the vehicle editor panel"""
        editor_frame = ttk.LabelFrame(self.left_frame, text="Vehicle Editor")
        editor_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Create form fields
        self.editor_vars = {}
        
        # Name
        ttk.Label(editor_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.editor_vars['name'] = tk.StringVar()
        ttk.Entry(editor_frame, textvariable=self.editor_vars['name'], width=25).grid(row=0, column=1, padx=5, pady=2)
        
        # Vehicle Type
        ttk.Label(editor_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.editor_vars['vehicle_type'] = tk.StringVar()
        type_combo = ttk.Combobox(editor_frame, textvariable=self.editor_vars['vehicle_type'], 
                                 values=self.pipeline.get_available_vehicle_types(), state="readonly", width=22)
        type_combo.grid(row=1, column=1, padx=5, pady=2)
        
        # Seed
        ttk.Label(editor_frame, text="Seed:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.editor_vars['seed'] = tk.IntVar(value=100)
        ttk.Entry(editor_frame, textvariable=self.editor_vars['seed'], width=25).grid(row=2, column=1, padx=5, pady=2)
        
        # Primary Color (Hull)
        ttk.Label(editor_frame, text="Hull Color:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        color_frame = ttk.Frame(editor_frame)
        color_frame.grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)
        
        self.color_button = tk.Button(color_frame, text="Choose Hull Color", command=self.choose_color, width=15)
        self.color_button.pack(side=tk.LEFT)
        self.current_color = (180, 180, 180)  # Default light grey
        self.update_color_button()
        
        # Secondary Color (Details)
        ttk.Label(editor_frame, text="Detail Color:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        secondary_color_frame = ttk.Frame(editor_frame)
        secondary_color_frame.grid(row=4, column=1, padx=5, pady=2, sticky=tk.W)
        
        self.secondary_color_button = tk.Button(secondary_color_frame, text="Choose Detail Color", command=self.choose_secondary_color, width=15)
        self.secondary_color_button.pack(side=tk.LEFT)
        self.current_secondary_color = (160, 160, 160)  # Default darker grey
        self.update_secondary_color_button()
        
        # Directions
        ttk.Label(editor_frame, text="Directions:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        self.editor_vars['n_dirs'] = tk.IntVar(value=8)
        dirs_combo = ttk.Combobox(editor_frame, textvariable=self.editor_vars['n_dirs'], 
                                 values=[4, 8, 16], state="readonly", width=22)
        dirs_combo.grid(row=5, column=1, padx=5, pady=2)
        
        # Image Size
        ttk.Label(editor_frame, text="Image Size:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        self.editor_vars['cell'] = tk.IntVar(value=512)
        size_combo = ttk.Combobox(editor_frame, textvariable=self.editor_vars['cell'], 
                                 values=[256, 512, 1024], state="readonly", width=22)
        size_combo.grid(row=6, column=1, padx=5, pady=2)
        
        # Update button
        ttk.Button(editor_frame, text="Update Vehicle", command=self.update_vehicle).grid(row=7, column=0, columnspan=2, pady=10)
        
        # Bind change events
        for var in self.editor_vars.values():
            if isinstance(var, (tk.StringVar, tk.IntVar)):
                var.trace('w', self.on_editor_change)
    
    def create_preview_panel(self):
        """Create the preview panel"""
        preview_frame = ttk.LabelFrame(self.right_frame, text="Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Preview canvas
        self.preview_canvas = tk.Canvas(preview_frame, bg='white', width=400, height=400)
        self.preview_canvas.pack(expand=True, padx=10, pady=10)
        
        # Preview controls
        control_frame = ttk.Frame(preview_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(control_frame, text="Generate Preview", command=self.generate_preview).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Clear Preview", command=self.clear_preview).pack(side=tk.LEFT)
    
    def create_generation_panel(self):
        """Create the generation control panel"""
        gen_frame = ttk.LabelFrame(self.right_frame, text="Generation")
        gen_frame.pack(fill=tk.X)
        
        # Output directory
        dir_frame = ttk.Frame(gen_frame)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(dir_frame, text="Output Directory:").pack(side=tk.LEFT)
        self.output_dir = tk.StringVar(value="out/vehicles")
        ttk.Entry(dir_frame, textvariable=self.output_dir, width=30).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(dir_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.RIGHT)
        
        # Generation options
        options_frame = ttk.Frame(gen_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.generate_debug = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Generate debug views", variable=self.generate_debug).pack(side=tk.LEFT)

        self.export_3d = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Export 3D meshes (GLB)", variable=self.export_3d).pack(side=tk.LEFT, padx=(10, 0))
        
        # Generation buttons
        button_frame = ttk.Frame(gen_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Generate Selected", command=self.generate_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Generate All", command=self.generate_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Stop", command=self.stop_generation).pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(gen_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
    
    def create_status_bar(self):
        """Create the status bar at the bottom of the window"""
        # Create a frame for the status bar to give it proper spacing
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        
        # Create the status label with better styling
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        status_bar.pack(fill=tk.X)
    
    def load_demo_vehicles(self):
        """Load demo vehicles into the list"""
        demo_specs = PresetConfigurations.create_demo_batch()
        self.vehicle_specs = demo_specs
        self.refresh_vehicle_list()
        self.status_var.set(f"Loaded {len(demo_specs)} demo vehicles")
    
    def refresh_vehicle_list(self):
        """Refresh the vehicle listbox"""
        self.vehicle_listbox.delete(0, tk.END)
        for spec in self.vehicle_specs:
            display_name = f"{spec.name} ({spec.vehicle_type})"
            self.vehicle_listbox.insert(tk.END, display_name)
    
    def on_vehicle_select(self, event):
        """Handle vehicle selection"""
        selection = self.vehicle_listbox.curselection()
        if selection:
            idx = selection[0]
            spec = self.vehicle_specs[idx]
            self.load_vehicle_to_editor(spec)
    
    def load_vehicle_to_editor(self, spec: VehicleSpec):
        """Load a vehicle spec into the editor"""
        self.editor_vars['name'].set(spec.name)
        self.editor_vars['vehicle_type'].set(spec.vehicle_type)
        self.editor_vars['seed'].set(spec.seed)
        self.editor_vars['n_dirs'].set(spec.n_dirs)
        self.editor_vars['cell'].set(spec.cell)
        self.current_color = spec.color
        self.current_secondary_color = spec.secondary_color
        self.update_color_button()
        self.update_secondary_color_button()
    
    def update_color_button(self):
        """Update the primary color button appearance"""
        color_hex = f"#{self.current_color[0]:02x}{self.current_color[1]:02x}{self.current_color[2]:02x}"
        self.color_button.config(bg=color_hex)
    
    def update_secondary_color_button(self):
        """Update the secondary color button appearance"""
        color_hex = f"#{self.current_secondary_color[0]:02x}{self.current_secondary_color[1]:02x}{self.current_secondary_color[2]:02x}"
        self.secondary_color_button.config(bg=color_hex)
    
    def choose_color(self):
        """Open color chooser dialog for primary color"""
        color = colorchooser.askcolor(initialcolor=self.current_color)
        if color[0]:  # User didn't cancel
            self.current_color = tuple(int(c) for c in color[0])
            self.update_color_button()
    
    def choose_secondary_color(self):
        """Open color chooser dialog for secondary color"""
        color = colorchooser.askcolor(initialcolor=self.current_secondary_color)
        if color[0]:  # User didn't cancel
            self.current_secondary_color = tuple(int(c) for c in color[0])
            self.update_secondary_color_button()
    
    def add_vehicle(self):
        """Add a new vehicle"""
        new_spec = VehicleSpec(
            name=f"vehicle_{len(self.vehicle_specs) + 1}",
            vehicle_type="tank",
            seed=100,
            color=(70, 110, 200)
        )
        self.vehicle_specs.append(new_spec)
        self.refresh_vehicle_list()
        # Select the new vehicle
        self.vehicle_listbox.selection_set(len(self.vehicle_specs) - 1)
        self.load_vehicle_to_editor(new_spec)
    
    def remove_vehicle(self):
        """Remove selected vehicle"""
        selection = self.vehicle_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.vehicle_specs[idx]
            self.refresh_vehicle_list()
    
    def duplicate_vehicle(self):
        """Duplicate selected vehicle"""
        selection = self.vehicle_listbox.curselection()
        if selection:
            idx = selection[0]
            original = self.vehicle_specs[idx]
            duplicate = VehicleSpec(
                name=f"{original.name}_copy",
                vehicle_type=original.vehicle_type,
                seed=original.seed + 1,
                color=original.color,
                secondary_color=original.secondary_color,  # Include secondary color!
                n_dirs=original.n_dirs,
                cell=original.cell,
                generate_debug=original.generate_debug,
                custom_params=original.custom_params.copy() if original.custom_params else None
            )
            self.vehicle_specs.append(duplicate)
            self.refresh_vehicle_list()
    
    def update_vehicle(self):
        """Update the selected vehicle with editor values"""
        selection = self.vehicle_listbox.curselection()
        if selection:
            idx = selection[0]
            spec = self.vehicle_specs[idx]
            
            spec.name = self.editor_vars['name'].get()
            spec.vehicle_type = self.editor_vars['vehicle_type'].get()
            spec.seed = self.editor_vars['seed'].get()
            spec.color = self.current_color
            spec.secondary_color = self.current_secondary_color
            spec.n_dirs = self.editor_vars['n_dirs'].get()
            spec.cell = self.editor_vars['cell'].get()
            spec.generate_debug = self.generate_debug.get()
            
            self.refresh_vehicle_list()
            self.vehicle_listbox.selection_set(idx)
    
    def on_editor_change(self, *args):
        """Handle editor field changes"""
        # Auto-update could be implemented here
        pass
    
    def generate_preview(self):
        """Generate a preview of the selected vehicle"""
        selection = self.vehicle_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a vehicle to preview.")
            return
        
        idx = selection[0]
        spec = self.vehicle_specs[idx]
        
        # Update spec with current editor values
        self.update_vehicle()
        
        # Generate preview in a separate thread
        def preview_thread():
            try:
                self.status_var.set("Generating preview...")
                
                # Create a temporary spec for preview (single frame)
                preview_spec = VehicleSpec(
                    name="preview",
                    vehicle_type=spec.vehicle_type,
                    seed=spec.seed,
                    color=spec.color,
                    secondary_color=spec.secondary_color,  # Include secondary color!
                    n_dirs=1,  # Just one direction for preview
                    cell=256,  # Smaller for faster preview
                    generate_debug=False
                )
                
                # Generate the vehicle
                result = self.pipeline.generate_vehicle(preview_spec, "temp/preview")
                
                # Load and display the preview
                if result and 'frames' in result and result['frames']:
                    self.display_preview_image(result['frames'][0])
                
                self.status_var.set("Preview generated")
                
            except Exception as e:
                messagebox.showerror("Preview Error", f"Failed to generate preview: {str(e)}")
                self.status_var.set("Preview failed")
        
        threading.Thread(target=preview_thread, daemon=True).start()
    
    def display_preview_image(self, image_path):
        """Display an image in the preview canvas"""
        try:
            # Load and resize image
            img = Image.open(image_path)
            img.thumbnail((350, 350), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.current_preview = ImageTk.PhotoImage(img)
            
            # Clear canvas and display image
            self.preview_canvas.delete("all")
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:  # Canvas is initialized
                x = canvas_width // 2
                y = canvas_height // 2
                self.preview_canvas.create_image(x, y, image=self.current_preview)
            
        except Exception as e:
            print(f"Error displaying preview: {e}")
    
    def clear_preview(self):
        """Clear the preview canvas"""
        self.preview_canvas.delete("all")
        self.current_preview = None
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)
    
    def generate_selected(self):
        """Generate the selected vehicle"""
        selection = self.vehicle_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a vehicle to generate.")
            return
        
        idx = selection[0]
        spec = self.vehicle_specs[idx]
        self.update_vehicle()  # Ensure spec is up to date
        
        self.start_generation([spec])
    
    def generate_all(self):
        """Generate all vehicles"""
        if not self.vehicle_specs:
            messagebox.showwarning("No Vehicles", "No vehicles to generate.")
            return
        
        self.start_generation(self.vehicle_specs)
    
    def start_generation(self, specs: List[VehicleSpec]):
        """Start generation in a separate thread"""
        if self.generation_thread and self.generation_thread.is_alive():
            messagebox.showwarning("Generation in Progress", "Generation is already in progress.")
            return
        
        def generation_thread():
            try:
                self.progress_var.set(0)
                total = len(specs)
                
                for i, spec in enumerate(specs):
                    if hasattr(self, '_stop_generation') and self._stop_generation:
                        break
                    
                    self.status_var.set(f"Generating {spec.name} ({i+1}/{total})")
                    
                    # Update spec with generation settings
                    spec.generate_debug = self.generate_debug.get()
                    spec.export_3d = self.export_3d.get()
                    
                    # Generate vehicle
                    self.pipeline.generate_vehicle(spec, self.output_dir.get())
                    
                    # Update progress
                    progress = ((i + 1) / total) * 100
                    self.progress_var.set(progress)
                
                if not (hasattr(self, '_stop_generation') and self._stop_generation):
                    self.status_var.set(f"Generation complete! Generated {total} vehicles.")
                    # Remove popup message - status bar message is sufficient
                else:
                    self.status_var.set("Generation stopped by user.")
                
                self.progress_var.set(0)
                
            except Exception as e:
                messagebox.showerror("Generation Error", f"Generation failed: {str(e)}")
                self.status_var.set("Generation failed")
                self.progress_var.set(0)
            
            finally:
                if hasattr(self, '_stop_generation'):
                    delattr(self, '_stop_generation')
        
        self.generation_thread = threading.Thread(target=generation_thread, daemon=True)
        self.generation_thread.start()
    
    def stop_generation(self):
        """Stop the current generation"""
        self._stop_generation = True
        self.status_var.set("Stopping generation...")
    
    def load_preset(self):
        """Load a preset configuration"""
        presets = {
            "Standard Vehicles": PresetConfigurations.create_demo_batch(),
            "Blue Faction": PresetConfigurations.create_faction_vehicles("blue", (70, 110, 200)),
            "Green Faction": PresetConfigurations.create_faction_vehicles("green", (70, 170, 95)),
        }
        
        # Simple dialog to choose preset
        preset_window = tk.Toplevel(self.root)
        preset_window.title("Load Preset")
        preset_window.geometry("300x200")
        preset_window.transient(self.root)
        preset_window.grab_set()
        
        ttk.Label(preset_window, text="Choose a preset:").pack(pady=10)
        
        preset_var = tk.StringVar()
        for preset_name in presets.keys():
            ttk.Radiobutton(preset_window, text=preset_name, variable=preset_var, value=preset_name).pack(anchor=tk.W, padx=20)
        
        def load_selected():
            if preset_var.get():
                self.vehicle_specs = presets[preset_var.get()]
                self.refresh_vehicle_list()
                self.status_var.set(f"Loaded preset: {preset_var.get()}")
                preset_window.destroy()
        
        ttk.Button(preset_window, text="Load", command=load_selected).pack(pady=10)
        ttk.Button(preset_window, text="Cancel", command=preset_window.destroy).pack()
    
    def save_configuration(self):
        """Save current configuration to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                config_data = []
                for spec in self.vehicle_specs:
                    config_data.append({
                        "name": spec.name,
                        "vehicle_type": spec.vehicle_type,
                        "seed": spec.seed,
                        "color": spec.color,
                        "secondary_color": spec.secondary_color,
                        "n_dirs": spec.n_dirs,
                        "cell": spec.cell,
                        "generate_debug": spec.generate_debug,
                        "export_3d": spec.export_3d,
                        "custom_params": spec.custom_params
                    })
                
                with open(filename, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                self.status_var.set(f"Configuration saved to {filename}")
                
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save configuration: {str(e)}")
    
    def load_configuration(self):
        """Load configuration from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    config_data = json.load(f)
                
                self.vehicle_specs = []
                for item in config_data:
                    spec = VehicleSpec(
                        name=item["name"],
                        vehicle_type=item["vehicle_type"],
                        seed=item["seed"],
                        color=tuple(item["color"]),
                        secondary_color=tuple(item["secondary_color"]) if "secondary_color" in item else (160, 160, 160),
                        n_dirs=item.get("n_dirs", 8),
                        cell=item.get("cell", 512),
                        generate_debug=item.get("generate_debug", True),
                        export_3d=item.get("export_3d", False),
                        custom_params=item.get("custom_params")
                    )
                    self.vehicle_specs.append(spec)
                
                self.refresh_vehicle_list()
                self.status_var.set(f"Configuration loaded from {filename}")
                
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load configuration: {str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """2D RTS Vehicle Generator

A tool for generating 3D vehicle models and rendering them as 2D sprite sheets for RTS games.

Features:
• Multiple vehicle types (tanks, APCs, artillery)
• Procedural generation with seeds
• Faction colors
• Isometric rendering
• Sprite sheet generation
• Debug views

Created with Python, Trimesh, and PyRender."""
        
        messagebox.showinfo("About", about_text)


def main():
    """Main function to run the GUI application"""
    root = tk.Tk()
    app = VehicleGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
