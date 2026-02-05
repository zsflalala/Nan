import slangpy as spy
from scene import Scene
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class OrthoFrustumConfig:
    """
    正交视锥体配置
    
    Attributes:
        center: 视锥体中心点 (世界坐标)，默认为原点
        radius: 正交投影的半宽/半高 (单位: 米)
        distance: 虚拟光源相机到中心点的距离 (单位: 米)
    """
    center: Optional[spy.float3] = None
    radius: float = 2.5
    distance: float = 10.0
    
    @property
    def near(self) -> float:
        """近平面距离"""
        return 0.0
    
    @property
    def far(self) -> float:
        """远平面距离，确保覆盖从光源到中心点再延伸的区域"""
        return self.distance + self.radius * 2.0
    
    def get_center(self) -> spy.float3:
        """获取中心点，默认为原点"""
        return self.center if self.center is not None else spy.float3(0, 0, 0)

class ShadowMapPass:
    def __init__(self, device: spy.Device, shadow_map_size=2048):
        self.device = device
        self.size = shadow_map_size
        self.program = device.load_program("shadow_map.slang", ["compute_main"])
        self.pipeline = device.create_compute_pipeline(self.program)
        
        # 正交视锥体配置 (可在外部修改)
        self.frustum_config = OrthoFrustumConfig()
        
        self.shadow_map = device.create_texture(
             width=self.size,
             height=self.size,
             format=spy.Format.r32_float,
             usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
             label="shadow_map"
        )

    def get_light_view_data(self, sun_direction):
        cfg = self.frustum_config
        center = cfg.get_center()
        light_dir = -sun_direction 

        eye = center - light_dir * cfg.distance
        target = center
        
        up = spy.float3(0, 1, 0)
        if abs(spy.math.dot(light_dir, up)) > 0.99:
            up = spy.float3(0, 0, 1)
        view = spy.math.matrix_from_look_at(eye, target, up)
        inv_view = spy.math.inverse(view)
        
        proj = spy.math.ortho(
            -cfg.radius, cfg.radius,   # left, right
            -cfg.radius, cfg.radius,   # bottom, top
            cfg.near, cfg.far          # near, far
        )
        
        vp = spy.math.mul(proj, view)
        
        return {
            "view": view,
            "inv_view": inv_view,
            "proj": proj,
            "vp": vp,
            "light_dir": light_dir,
            "ortho_size": cfg.radius,
            "near": cfg.near,
            "far": cfg.far
        }

    def execute(self, command_encoder: spy.CommandEncoder, scene: Scene, sun_direction: spy.float3):
        # Compute Matrices and Data
        data = self.get_light_view_data(sun_direction)
        
        # Update Scene for other passes 
        scene.shadow_map = self.shadow_map
        scene.light_view_proj = data["vp"]
        
        # Dispatch using pipeline
        with command_encoder.begin_compute_pass() as pass_encoder:
            shader_object = pass_encoder.bind_pipeline(self.pipeline)
            cursor = spy.ShaderCursor(shader_object)
            
            # Helper to access generator params
            g = cursor.g_generator
            g.shadow_map = self.shadow_map
            
            # Pass Assignment-specific parameters to Shader
            g.light_view_matrix = data["view"]
            g.inv_light_view_matrix = data["inv_view"] 
            g.light_direction = data["light_dir"]
            g.ortho_size = data["ortho_size"]
            g.near_plane = data["near"]
            g.far_plane = data["far"]
            
            scene.bind(cursor.g_scene)
            
            pass_encoder.dispatch(thread_count=[self.size, self.size, 1])
