import slangpy as spy
from scene import Scene
import math

class ShadowMapPass:
    def __init__(self, device: spy.Device, scene: Scene, shadow_map_size=2048):
        self.device = device
        self.scene = scene
        self.size = shadow_map_size
        self.program = device.load_program("shadow_map.slang", ["compute_main"])
        self.pipeline = device.create_compute_pipeline(self.program)
        
        self.shadow_map = device.create_texture(
             width=self.size,
             height=self.size,
             format=spy.Format.r32_float,
             usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
             label="shadow_map"
        )
        # Default matrices just in case
        self.scene.shadow_map = self.shadow_map
        self.scene.light_view_proj = spy.float4x4.identity()
        self.scene.shadow_map_size = float(self.size)

    def execute(self, command_encoder: spy.CommandEncoder):
        # 1. Compute Matrices
        sun_dir = self.scene.sun_direction
        light_dir = -sun_dir 

        center = spy.float3(0, 2, 0)
        radius = 8.0 
        
        # Position camera "at sun" (far away)
        distance = 20.0
        eye = center - light_dir * distance
        target = center
        up = spy.float3(0, 1, 0)
        # Handle case where light_dir is vertical
        if abs(spy.math.dot(light_dir, up)) > 0.99:
            up = spy.float3(0, 0, 1)

        view = spy.math.matrix_from_look_at(eye, target, up)
        
        # Orthographic Projection
        w = radius
        h = radius
        near = 0.0
        far = distance + radius * 2.0
        
        proj = spy.math.ortho(-w, w, -h, h, near, far)
        
        # Combined VP
        vp = spy.math.mul(proj, view)
        inv_vp = spy.math.inverse(vp)
        
        # Update Scene for other passes 
        self.scene.shadow_map = self.shadow_map
        self.scene.light_view_proj = vp
        
        # Dispatch using pipeline (similar to PathTracer)
        with command_encoder.begin_compute_pass() as pass_encoder:
            shader_object = pass_encoder.bind_pipeline(self.pipeline)
            cursor = spy.ShaderCursor(shader_object)
            
            cursor.g_generator.shadow_map = self.shadow_map
            cursor.g_generator.light_view_proj = vp
            cursor.g_generator.inv_light_view_proj = inv_vp
            
            self.scene.bind(cursor.g_scene)
            
            pass_encoder.dispatch(thread_count=[self.size, self.size, 1])
