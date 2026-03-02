import slangpy as spy
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class FrustumData:
    """Data structure for frustum visualization."""
    corners: List[spy.float3]  # 8 corners of the box
    edges: List[Tuple[int, int]]  # 12 edges as index pairs
    light_pos: spy.float3  # Virtual light position
    light_dir: spy.float3  # Light direction

class DebugVisualizer:
    """
    Debug visualization tool for shadow map frustum and related debugging features.
    
    This class manages its own UI and can be easily disabled/removed for release builds.
    """
    
    BOX_EDGES = [
        # Near face edges
        (0, 1), (1, 3), (3, 2), (2, 0),
        # Far face edges
        (4, 5), (5, 7), (7, 6), (6, 4),
        # Connecting edges (near to far)
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    
    def __init__(self, device: spy.Device):
        self.device = device
        self.enabled = True
        self.line_color = spy.float3(1.0, 0.8, 0.0)  # Yellow
        self.line_thickness = 2.0  # Pixels
        
        # Shadow map preview settings
        self.preview_size = 256  # Preview window size in pixels
        self.preview_margin = 20  # Margin from bottom-right corner
        
        # UI elements
        self.ui_window: Optional[spy.ui.Window] = None
        self.show_frustum_checkbox: Optional[spy.ui.CheckBox] = None
        self.show_shadow_map_checkbox: Optional[spy.ui.CheckBox] = None
        self.frustum_radius_slider: Optional[spy.ui.SliderFloat] = None
        self.frustum_distance_slider: Optional[spy.ui.SliderFloat] = None
        
        # Reference to shadow pass for config updates
        self._shadow_pass = None
        
        # Load wireframe shader
        self.program = device.load_program("debug_visualizer.slang", ["compute_main"])
        self.pipeline = device.create_compute_pipeline(self.program)
        
        # Load shadow map preview shader
        self.preview_program = device.load_program("debug_visualizer.slang", ["shadow_map_preview_main"])
        self.preview_pipeline = device.create_compute_pipeline(self.preview_program)
        
        # Create buffer for edge data (12 edges * 2 endpoints * 3 floats)
        self.edge_buffer = device.create_buffer(
            size=12 * 2 * 3 * 4,  # 12 edges, 2 points each, 3 floats, 4 bytes per float
            usage=spy.BufferUsage.shader_resource,
            label="debug_edge_buffer"
        )
    
    def setup_ui(self, ui_context: spy.ui.Context, shadow_pass=None):
        """
        Setup debug UI window.
        
        Args:
            ui_context: SlangPy UI context
            shadow_pass: Optional ShadowMapPass for frustum config sliders
        """
        self._shadow_pass = shadow_pass
        
        self.ui_window = spy.ui.Window(
            ui_context.screen, 
            "Debug Visualization", 
            spy.float2(420, 10), 
            spy.float2(450, 180)
        )
        
        # Debug toggles
        self.show_frustum_checkbox = spy.ui.CheckBox(
            self.ui_window, 'Show Light Frustum'
        )
        self.show_shadow_map_checkbox = spy.ui.CheckBox(
            self.ui_window, 'Show Shadow Map'
        )
        
        # Frustum configuration sliders (only if shadow pass provided)
        if shadow_pass is not None:
            cfg = shadow_pass.frustum_config
            self.frustum_radius_slider = spy.ui.SliderFloat(
                self.ui_window, 'Frustum Radius', min=1.0, max=50.0, value=cfg.radius
            )
            self.frustum_distance_slider = spy.ui.SliderFloat(
                self.ui_window, 'Frustum Distance', min=10.0, max=40.0, value=cfg.distance
            )
    
    def update(self):
        """Update configurations from UI. Call this each frame."""
        if self._shadow_pass is None:
            return
        
        cfg = self._shadow_pass.frustum_config
        
        if self.frustum_radius_slider is not None:
            cfg.radius = self.frustum_radius_slider.value
        
        if self.frustum_distance_slider is not None:
            cfg.distance = self.frustum_distance_slider.value
    
    @property
    def show_frustum(self) -> bool:
        """Whether to show the light frustum visualization."""
        if self.show_frustum_checkbox is None:
            return False
        return self.show_frustum_checkbox.value
    
    @property
    def show_shadow_map(self) -> bool:
        """Whether to show the shadow map preview."""
        if self.show_shadow_map_checkbox is None:
            return False
        return self.show_shadow_map_checkbox.value
    
    def compute_frustum_corners(
        self,
        center: spy.float3,
        light_dir: spy.float3,
        radius: float,
        distance: float,
        near: float,
        far: float
    ) -> FrustumData:
        """
        Compute the 8 corners of the orthographic frustum in world space.
        
        Args:
            center: Frustum center point in world space
            light_dir: Normalized light direction (pointing from light to scene)
            radius: Half-width/height of the orthographic projection
            distance: Distance from center to light position
            near: Near plane distance
            far: Far plane distance
            
        Returns:
            FrustumData with corners, edges, and light info
        """
        # Light position (virtual camera position)
        light_pos = center - light_dir * distance
        
        # Build orthonormal basis for light space
        up = spy.float3(0, 1, 0)
        if abs(spy.math.dot(light_dir, up)) > 0.99:
            up = spy.float3(0, 0, 1)
        
        right = spy.math.normalize(spy.math.cross(light_dir, up))
        up = spy.math.normalize(spy.math.cross(right, light_dir))
        
        # Compute 8 corners
        # Near plane corners (relative to light_pos)
        corners = []
        for z_offset, z_dist in [(near, near), (far, far)]:
            # Point along light direction at this z distance
            plane_center = light_pos + light_dir * z_dist
            
            for y_sign in [-1, 1]:
                for x_sign in [-1, 1]:
                    corner = (
                        plane_center 
                        + right * (x_sign * radius)
                        + up * (y_sign * radius)
                    )
                    corners.append(corner)
        
        return FrustumData(
            corners=corners,
            edges=self.BOX_EDGES,
            light_pos=light_pos,
            light_dir=light_dir
        )
    
    def get_frustum_from_shadow_pass(self, shadow_pass, sun_direction: spy.float3) -> FrustumData:
        """
        Extract frustum data from a ShadowMapPass instance.
        
        Args:
            shadow_pass: ShadowMapPass instance
            sun_direction: Current sun direction
            
        Returns:
            FrustumData for the shadow map's orthographic view
        """
        cfg = shadow_pass.frustum_config
        center = cfg.get_center()
        light_dir = -sun_direction  # Light comes from opposite of sun direction
        
        return self.compute_frustum_corners(
            center=center,
            light_dir=light_dir,
            radius=cfg.radius,
            distance=cfg.distance,
            near=cfg.near,
            far=cfg.far
        )
    
    def _update_edge_buffer(self, frustum: FrustumData):
        """Update the GPU buffer with edge endpoint data."""
        import numpy as np
        
        # Pack edge data: for each edge, store start and end points
        data = []
        for i0, i1 in frustum.edges:
            p0 = frustum.corners[i0]
            p1 = frustum.corners[i1]
            data.extend([p0.x, p0.y, p0.z])
            data.extend([p1.x, p1.y, p1.z])
        
        # Convert to numpy array and upload
        np_data = np.array(data, dtype=np.float32)
        self.edge_buffer.copy_from_numpy(np_data)
    
    def execute(
        self,
        command_encoder: spy.CommandEncoder,
        output: spy.Texture,
        frustum: FrustumData,
        camera_pos: spy.float3,
        inv_view_proj: spy.float4x4
    ):
        """
        Render the debug visualization overlay.
        
        Args:
            command_encoder: Command encoder for GPU commands
            output: Output texture to draw on (will be modified in-place)
            frustum: Frustum data to visualize
            camera_pos: Camera position for ray generation
            inv_view_proj: Inverse view-projection matrix for screen-to-world rays
        """
        if not self.enabled:
            return
        
        # Update edge buffer
        self._update_edge_buffer(frustum)
        
        # Execute compute shader
        with command_encoder.begin_compute_pass() as pass_encoder:
            shader_object = pass_encoder.bind_pipeline(self.pipeline)
            cursor = spy.ShaderCursor(shader_object)
            
            g = cursor.g_debug
            g.output = output
            g.edge_count = len(frustum.edges)
            g.edge_buffer = self.edge_buffer
            g.camera_pos = camera_pos
            g.inv_view_proj = inv_view_proj
            g.line_color = self.line_color
            g.line_thickness = self.line_thickness
            g.image_width = output.width
            g.image_height = output.height
            
            pass_encoder.dispatch(thread_count=[output.width, output.height, 1])

    def draw_shadow_map_preview(
        self,
        command_encoder: spy.CommandEncoder,
        output: spy.Texture,
        shadow_map: spy.Texture
    ):
        """
        Draw shadow map texture as a preview in the corner of the screen.
        
        Args:
            command_encoder: Command encoder for GPU commands
            output: Output texture to draw on
            shadow_map: Shadow map texture to preview
        """
        # Calculate preview position (bottom-right corner)
        preview_x = output.width - self.preview_size - self.preview_margin
        preview_y = output.height - self.preview_size - self.preview_margin
        
        # Execute preview shader
        with command_encoder.begin_compute_pass() as pass_encoder:
            shader_object = pass_encoder.bind_pipeline(self.preview_pipeline)
            cursor = spy.ShaderCursor(shader_object)
            
            g = cursor.g_preview
            g.output = output
            g.shadow_map = shadow_map
            g.preview_x = preview_x
            g.preview_y = preview_y
            g.preview_size = self.preview_size
            g.image_width = output.width
            g.image_height = output.height
            
            pass_encoder.dispatch(thread_count=[self.preview_size, self.preview_size, 1])
