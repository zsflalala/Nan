from slangpy import Device

import slangpy as spy
from scene import Scene
from tone_mapper import ToneMapper
from accumulator import Accumulator
from path_tracer import PathTracer
from shadow_map import ShadowMapPass
from render_data import RenderData

class PathTracingRenderer:
    def initialize(self, device: spy.Device, scene: Scene):
        self.device: Device = device
        self.scene: Scene = scene
        self.path_tracer: PathTracer = PathTracer(device, scene)
        self.accumulator: Accumulator = Accumulator(device, resource_key="path_tracing_renderer.accumulator_history")
        self.tone_mapper: ToneMapper = ToneMapper(device)
        self.shadow_map_pass: ShadowMapPass = ShadowMapPass(device, scene)
        self.exposure_slider = None

        self.render_texture: spy.Texture | None = None
        self.accum_texture: spy.Texture | None = None

        scene.event_distpacher.subscribe("camera_move", self.on_camera_move)

        self.reset_accumulator = True
        self.use_accum_check_box: spy.ui.CheckBox | None = None
        self.use_shadow_map_check_box: spy.ui.CheckBox | None = None

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
        if use_shadow_map:
            self.shadow_map_pass.execute(command_encoder)

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