from slangpy import Device

import slangpy as spy
from scene import Scene
from tone_mapper import ToneMapper
from accumulator import Accumulator
from path_tracer import PathTracer
from shadow_map import ShadowMapPass
from render_data import RenderData
from debug_visualizer import DebugVisualizer

class PathTracingRenderer:
    def initialize(self, device: spy.Device, scene: Scene):
        self.device: Device = device
        self.scene: Scene = scene
        self.path_tracer: PathTracer = PathTracer(device, scene)
        self.accumulator: Accumulator = Accumulator(device, resource_key="path_tracing_renderer.accumulator_history")
        self.tone_mapper: ToneMapper = ToneMapper(device)
        
        # Initialize ShadowMapPass with size from scene
        shadow_map_size = int(scene.shadow_map_size) if hasattr(scene, 'shadow_map_size') else 2048
        print(f"[PathTracingRenderer] Initializing ShadowMapPass with size: {shadow_map_size}")
        self.shadow_map_pass: ShadowMapPass = ShadowMapPass(device, shadow_map_size)
        
        self.exposure_slider = None

        self.render_texture: spy.Texture | None = None
        self.accum_texture: spy.Texture | None = None

        scene.event_distpacher.subscribe("camera_move", self.on_camera_move)

        self.reset_accumulator = True
        self.use_accum_check_box: spy.ui.CheckBox | None = None
        self.use_shadow_map_check_box: spy.ui.CheckBox | None = None
        
        # Shadow filter UI elements
        self.shadow_filter_hard_checkbox: spy.ui.CheckBox | None = None
        self.shadow_filter_pcf_checkbox: spy.ui.CheckBox | None = None
        self.shadow_filter_pcss_checkbox: spy.ui.CheckBox | None = None
        self.pcf_radius_slider: spy.ui.SliderFloat | None = None
        self.pcss_light_size_slider: spy.ui.SliderFloat | None = None
        self._shadow_ui_window: spy.ui.Window | None = None
        self._ui_context: spy.ui.Context | None = None
        self._current_shadow_filter_mode: int = 0  # Track current mode for UI rebuild
        
        # Debug visualizer (可在发布时移除此行及相关调用)
        self.debug_visualizer: DebugVisualizer = DebugVisualizer(device)

    def on_camera_move(self, data):
        self.reset_accumulator = True

    def render(
        self,
        command_encoder: spy.CommandEncoder,
        output: spy.Texture,
        frame: int,
        device: spy.Device,
        scene: Scene,
        render_data: RenderData,
    ):
        render_texture = render_data.get_texture(
            "path_tracing_renderer.render_texture",
            width=output.width,
            height=output.height,
            format=spy.Format.rgba32_float,
            usage=spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access,
            label="render_texture",
        )
        accum_texture = render_data.get_texture(
            "path_tracing_renderer.accum_texture",
            width=output.width,
            height=output.height,
            format=spy.Format.rgba32_float,
            usage=spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access,
            label="accum_texture",
        )
        self.render_texture = render_texture
        self.accum_texture = accum_texture

        # Update shadow map usage flag and execute if enabled
        use_shadow_map = self._get_use_shadow_map()
        self.scene.use_shadow_map = use_shadow_map
        self._update_shadow_filter_settings()
        
        # Update debug visualizer config from UI
        self.debug_visualizer.update()
        
        if use_shadow_map:
            self.shadow_map_pass.execute(command_encoder, self.scene, self.scene.sun_direction)

        self.path_tracer.execute(command_encoder, render_texture, frame)
        self.accumulator.execute(
            command_encoder,
            render_data,
            render_texture,
            accum_texture,
            self.reset_accumulator,
        )
        
        self.tone_mapper.exposure = self.exposure
        self.tone_mapper.execute(
            command_encoder,
            accum_texture if self._get_use_accum() else render_texture,
            output,
        )

        # Debug visualization (可在发布时移除此块)
        if self.debug_visualizer.show_frustum:
            frustum = self.debug_visualizer.get_frustum_from_shadow_pass(
                self.shadow_map_pass,
                self.scene.sun_direction
            )
            self.debug_visualizer.execute(
                command_encoder,
                output,
                frustum,
                self.scene.camera.position,
                self.scene.camera.inv_view_proj_matrix
            )
        
        if self.debug_visualizer.show_shadow_map:
            self.debug_visualizer.draw_shadow_map_preview(
                command_encoder,
                output,
                self.shadow_map_pass.shadow_map
            )

        self.reset_accumulator = False

    def _get_use_accum(self) -> bool:
        """Get use_accum value, handling both bool and UI checkbox."""
        if self.use_accum_check_box is None:
            return True
        return self.use_accum_check_box.value

    def _get_use_shadow_map(self) -> bool:
        """Get use_shadow_map value from UI checkbox."""
        if self.use_shadow_map_check_box is None:
            return True
        return self.use_shadow_map_check_box.value

    def _update_shadow_filter_settings(self):
        """Update shadow filter settings from UI to scene."""
        # Radio button behavior: find if a new checkbox was selected
        new_selection = -1
        checkboxes = [
            self.shadow_filter_hard_checkbox,
            self.shadow_filter_pcf_checkbox,
            self.shadow_filter_pcss_checkbox
        ]
        
        for i, checkbox in enumerate(checkboxes):
            if checkbox is not None and checkbox.value and i != self._current_shadow_filter_mode:
                new_selection = i
                break
        
        if new_selection >= 0:
            self._current_shadow_filter_mode = new_selection
            for i, checkbox in enumerate(checkboxes):
                if checkbox is not None:
                    checkbox.value = (i == self._current_shadow_filter_mode)
        else:
            # Ensure the current selection stays checked
            if checkboxes[self._current_shadow_filter_mode] is not None:
                checkboxes[self._current_shadow_filter_mode].value = True
        
        # Update scene settings
        self.scene.shadow_filter_mode = self._current_shadow_filter_mode
        
        if self.pcf_radius_slider is not None:
            self.scene.pcf_radius = self.pcf_radius_slider.value
        
        if self.pcss_light_size_slider is not None:
            self.scene.pcss_light_size = self.pcss_light_size_slider.value

    @property
    def exposure(self) -> float:
        """Get current exposure value from UI slider (safe access)."""
        slider = getattr(self, 'exposure_slider', None)
        if slider is not None:
            try:
                return slider.value
            except Exception:
                pass
        return 0.0

    def setup_ui(self, ui_context: spy.ui.Context, ui_window: spy.ui.Window):
        self._ui_context = ui_context         
        
        self.exposure_slider = spy.ui.SliderFloat(ui_window, 'Exposure', min=-5.0, max=5.0, value=0.0)
        self.use_accum_check_box = spy.ui.CheckBox(ui_window, 'Use Accum')
        
        # Shadow filtering UI window
        self._setup_shadow_filter_ui(ui_context)
        
        # Debug UI (可在发布时移除此行)
        self.debug_visualizer.setup_ui(ui_context, self.shadow_map_pass)
    
    def _setup_shadow_filter_ui(self, ui_context: spy.ui.Context):
        """Setup shadow filtering options UI window."""
        self._shadow_ui_window = spy.ui.Window(
            ui_context.screen, 
            "Shadow Filtering", 
            spy.float2(420, 200), 
            spy.float2(400, 220)  # Increased height for extra checkbox
        )
        
        # Master shadow switch
        self.use_shadow_map_check_box = spy.ui.CheckBox(self._shadow_ui_window, 'Use Shadow Map')
        
        # Hard Shadows (no parameters)
        self.shadow_filter_hard_checkbox = spy.ui.CheckBox(
            self._shadow_ui_window, 'Hard Shadows'
        )
        self.shadow_filter_hard_checkbox.value = True  # Default
        
        # PCF with its parameter slider below
        self.shadow_filter_pcf_checkbox = spy.ui.CheckBox(
            self._shadow_ui_window, 'PCF (Soft Edges)'
        )
        self.pcf_radius_slider = spy.ui.SliderFloat(
            self._shadow_ui_window, '  Radius', min=1.0, max=10.0, value=3.0
        )
        
        # PCSS with its parameter slider below
        self.shadow_filter_pcss_checkbox = spy.ui.CheckBox(
            self._shadow_ui_window, 'PCSS (Contact Hardening)'
        )
        self.pcss_light_size_slider = spy.ui.SliderFloat(
            self._shadow_ui_window, '  Light Size', min=0.1, max=5.0, value=1.0
        )