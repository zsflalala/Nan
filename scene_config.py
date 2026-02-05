# Scene Configuration
# 场景配置文件

from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum

PROJECT_DIR = Path(__file__).parent


class SceneType(Enum):
    """可用的场景类型"""
    DEMO = "demo"
    RANDOM_OBJECTS = "random_objects"
    BISTRO = "bistro"
    BISTROX = "bistrox"


# 可用的 Shadow Map 大小选项
SHADOW_MAP_SIZES = [1024, 2048, 4096, 8192]
DEFAULT_SHADOW_MAP_SIZE = 2048


@dataclass
class SceneConfig:
    """场景配置"""
    name: str
    scene_type: SceneType
    path: Optional[Path] = None
    scale: float = 0.1
    description: str = ""
    shadow_map_size: int = DEFAULT_SHADOW_MAP_SIZE
    
    @staticmethod
    def get_available_scenes() -> list["SceneConfig"]:
        """获取所有可用的场景配置"""
        bistro_dir = PROJECT_DIR / "Scene" / "bistro"
        
        scenes = [
            SceneConfig(
                name="Demo (Cornell Box)",
                scene_type=SceneType.DEMO,
                path=None,
                description="默认的 Cornell Box 演示场景"
            ),
            SceneConfig(
                name="Random Objects",
                scene_type=SceneType.RANDOM_OBJECTS,
                path=None,
                description="30x30 平面上随机摆放 9 个彩色物体"
            ),
        ]
        
        # 检查 Bistro 场景是否存在
        bistro_path = bistro_dir / "bistro.gltf"
        if bistro_path.exists():
            scenes.append(SceneConfig(
                name="Bistro (Standard)",
                scene_type=SceneType.BISTRO,
                path=bistro_path,
                scale=0.1,
                description="Amazon Lumberyard Bistro 标准版场景"
            ))
        
        # 检查 Bistrox 场景是否存在
        bistrox_path = bistro_dir / "bistrox.gltf"
        if bistrox_path.exists():
            scenes.append(SceneConfig(
                name="Bistro Extended",
                scene_type=SceneType.BISTROX,
                path=bistrox_path,
                scale=0.1,
                description="Amazon Lumberyard Bistro 扩展版场景"
            ))
        
        return scenes
