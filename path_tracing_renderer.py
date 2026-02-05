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
        self.shadow_map_pass: ShadowMapPass = ShadowMapPass(device)
        self.exposure_slider = None

        self.render_texture: spy.Texture | None = None
        self.accum_texture: spy.Texture | None = None

        scene.event_distpacher.subscribe("camera_move", self.on_camera_move)

        self.reset_accumulator = True
        self.use_accum_check_box: spy.ui.CheckBox | None = None
        self.use_shadow_map_check_box: spy.ui.CheckBox | None = None
        
        # [DEBUG] 
        self.debug_visualizer: DebugVisualizer = DebugVisualizer(device)
        self.debug_ui_window: spy.ui.Window | None = None
        self.debug_frustum_check_box: spy.ui.CheckBox | None = None
        self.debug_shadow_map_check_box: spy.ui.CheckBox | None = None
        self.frustum_radius_slider: spy.ui.SliderFloat | None = None
        self.frustum_distance_slider: spy.ui.SliderFloat | None = None

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
        
        # [DEBUG]
        self._update_frustum_config()
        
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

        # [DEBUG] 调试可视化渲染，发布时可删除
        if self._get_debug_frustum():
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
        
        # 绘制 Shadow Map 纹理预览
        if self._get_debug_shadow_map():
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

    # [DEBUG] 
    def _get_debug_frustum(self) -> bool:
        """Get debug_frustum value from UI checkbox."""
        if self.debug_frustum_check_box is None:
            return False
        return self.debug_frustum_check_box.value

    # [DEBUG] 
    def _get_debug_shadow_map(self) -> bool:
        """Get debug_shadow_map value from UI checkbox."""
        if self.debug_shadow_map_check_box is None:
            return False
        return self.debug_shadow_map_check_box.value

    def _update_frustum_config(self):
        """Update shadow map frustum config from UI sliders."""
        cfg = self.shadow_map_pass.frustum_config
        
        if self.frustum_radius_slider is not None:
            cfg.radius = self.frustum_radius_slider.value
        
        if self.frustum_distance_slider is not None:
            cfg.distance = self.frustum_distance_slider.value

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
        self.exposure_slider = spy.ui.SliderFloat(ui_window, 'Exposure', min=-5.0, max=5.0, value=0.0)
        self.use_accum_check_box = spy.ui.CheckBox(ui_window, 'Use Accum')
        self.use_shadow_map_check_box = spy.ui.CheckBox(ui_window, 'Use Shadow Map')
        
        # [DEBUG] 创建独立的调试 UI 窗口，发布时可删除
        self._setup_debug_ui(ui_context)

    def _setup_debug_ui(self, ui_context: spy.ui.Context):
        """Setup separate debug UI window. Can be removed for release."""
        self.debug_ui_window = spy.ui.Window(
            ui_context.screen, "Debug Visualization", spy.float2(420, 10), spy.float2(300, 180)
        )
        
        # Debug toggles
        self.debug_frustum_check_box = spy.ui.CheckBox(
            self.debug_ui_window, 'Show Light Frustum'
        )
        self.debug_shadow_map_check_box = spy.ui.CheckBox(
            self.debug_ui_window, 'Show Shadow Map'
        )
        
        # Frustum configuration sliders
        cfg = self.shadow_map_pass.frustum_config
        self.frustum_radius_slider = spy.ui.SliderFloat(
            self.debug_ui_window, 'Frustum Radius', min=1.0, max=5.0, value=cfg.radius
        )
        self.frustum_distance_slider = spy.ui.SliderFloat(
            self.debug_ui_window, 'Frustum Distance', min=10.0, max=40.0, value=cfg.distance
        )