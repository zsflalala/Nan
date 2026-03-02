import slangpy as spy
import numpy as np
import numpy.typing as npt


class Mesh:
    def __init__(
        self,
        vertices: npt.NDArray[np.float32],  # type: ignore
        indices: npt.NDArray[np.uint32],  # type: ignore
    ):
        super().__init__()
        assert vertices.ndim == 2 and vertices.dtype == np.float32
        assert indices.ndim == 2 and indices.dtype == np.uint32
        self.vertices = vertices
        self.indices = indices

    @property
    def vertex_count(self):
        return self.vertices.shape[0]

    @property
    def triangle_count(self):
        return self.indices.shape[0]

    @property
    def index_count(self):
        return self.triangle_count * 3

    @classmethod
    def create_triangle(
        cls,
        pos_a: npt.NDArray[np.float32],  # type: ignore
        pos_b: npt.NDArray[np.float32],  # type: ignore
        pos_c: npt.NDArray[np.float32],  # type: ignore
        normal_a: npt.NDArray[np.float32],  # type: ignore
        normal_b: npt.NDArray[np.float32],  # type: ignore
        normal_c: npt.NDArray[np.float32],  # type: ignore
    ):
        """
        Create a triangle mesh with specified positions and normals for each vertex.
        
        Args:
            pos_a, pos_b, pos_c: 3D positions of vertices A, B, C
            normal_a, normal_b, normal_c: 3D normals at vertices A, B, C
        """
        vertices = np.array(
            [
                # position, normal, uv
                [pos_a[0], pos_a[1], pos_a[2], normal_a[0], normal_a[1], normal_a[2], 0, 0],
                [pos_b[0], pos_b[1], pos_b[2], normal_b[0], normal_b[1], normal_b[2], 1, 0],
                [pos_c[0], pos_c[1], pos_c[2], normal_c[0], normal_c[1], normal_c[2], 0, 1],
            ],
            dtype=np.float32,
        )
        indices = np.array(
            [
                [0, 1, 2],
            ],
            dtype=np.uint32,
        )
        return Mesh(vertices, indices)

    @classmethod
    def create_quad(cls, size: "spy.float2param" = spy.float2(1)):
        vertices = np.array(
            [
                # position, normal, uv
                [-0.5, 0, -0.5, 0, 1, 0, 0, 0],
                [+0.5, 0, -0.5, 0, 1, 0, 1, 0],
                [-0.5, 0, +0.5, 0, 1, 0, 0, 1],
                [+0.5, 0, +0.5, 0, 1, 0, 1, 1],
            ],
            dtype=np.float32,
        )
        vertices[:, (0, 2)] *= [size[0], size[1]]
        indices = np.array(
            [
                [2, 1, 0],
                [1, 2, 3],
            ],
            dtype=np.uint32,
        )
        return Mesh(vertices, indices)

    @classmethod
    def create_quad_yz(cls, size: "spy.float2param" = spy.float2(1), face_positive_x: bool = True):
        """Create a quad in YZ plane. If face_positive_x=True, normal points +X, else -X."""
        nx = 1.0 if face_positive_x else -1.0
        vertices = np.array(
            [
                # position (x=0), normal, uv
                [0, -0.5, -0.5, nx, 0, 0, 0, 0],
                [0, +0.5, -0.5, nx, 0, 0, 1, 0],
                [0, -0.5, +0.5, nx, 0, 0, 0, 1],
                [0, +0.5, +0.5, nx, 0, 0, 1, 1],
            ],
            dtype=np.float32,
        )
        vertices[:, (1, 2)] *= [size[0], size[1]]
        if face_positive_x:
            # For normal +X, winding should give cross product pointing +X
            indices = np.array([[0, 1, 2], [3, 2, 1]], dtype=np.uint32)
        else:
            # For normal -X
            indices = np.array([[2, 1, 0], [1, 2, 3]], dtype=np.uint32)
        return Mesh(vertices, indices)

    @classmethod
    def create_quad_xy(cls, size: "spy.float2param" = spy.float2(1), face_positive_z: bool = True):
        """Create a quad in XY plane. If face_positive_z=True, normal points +Z, else -Z."""
        nz = 1.0 if face_positive_z else -1.0
        vertices = np.array(
            [
                # position (z=0), normal, uv
                [-0.5, -0.5, 0, 0, 0, nz, 0, 0],
                [+0.5, -0.5, 0, 0, 0, nz, 1, 0],
                [-0.5, +0.5, 0, 0, 0, nz, 0, 1],
                [+0.5, +0.5, 0, 0, 0, nz, 1, 1],
            ],
            dtype=np.float32,
        )
        vertices[:, (0, 1)] *= [size[0], size[1]]
        if face_positive_z:
            indices = np.array([[0, 1, 2], [3, 2, 1]], dtype=np.uint32)
        else:
            indices = np.array([[2, 1, 0], [1, 2, 3]], dtype=np.uint32)
        return Mesh(vertices, indices)

    @classmethod
    def create_cube(cls, size: "spy.float3param" = spy.float3(1)):
        vertices = np.array(
            [
                # position, normal, uv
                # left
                [-0.5, -0.5, -0.5, 0, -1, 0, 0.0, 0.0],
                [-0.5, -0.5, +0.5, 0, -1, 0, 1.0, 0.0],
                [+0.5, -0.5, +0.5, 0, -1, 0, 1.0, 1.0],
                [+0.5, -0.5, -0.5, 0, -1, 0, 0.0, 1.0],
                # right
                [-0.5, +0.5, +0.5, 0, +1, 0, 0.0, 0.0],
                [-0.5, +0.5, -0.5, 0, +1, 0, 1.0, 0.0],
                [+0.5, +0.5, -0.5, 0, +1, 0, 1.0, 1.0],
                [+0.5, +0.5, +0.5, 0, +1, 0, 0.0, 1.0],
                # back
                [-0.5, +0.5, -0.5, 0, 0, -1, 0.0, 0.0],
                [-0.5, -0.5, -0.5, 0, 0, -1, 1.0, 0.0],
                [+0.5, -0.5, -0.5, 0, 0, -1, 1.0, 1.0],
                [+0.5, +0.5, -0.5, 0, 0, -1, 0.0, 1.0],
                # front
                [+0.5, +0.5, +0.5, 0, 0, +1, 0.0, 0.0],
                [+0.5, -0.5, +0.5, 0, 0, +1, 1.0, 0.0],
                [-0.5, -0.5, +0.5, 0, 0, +1, 1.0, 1.0],
                [-0.5, +0.5, +0.5, 0, 0, +1, 0.0, 1.0],
                # bottom
                [-0.5, +0.5, +0.5, -1, 0, 0, 0.0, 0.0],
                [-0.5, -0.5, +0.5, -1, 0, 0, 1.0, 0.0],
                [-0.5, -0.5, -0.5, -1, 0, 0, 1.0, 1.0],
                [-0.5, +0.5, -0.5, -1, 0, 0, 0.0, 1.0],
                # top
                [+0.5, +0.5, -0.5, +1, 0, 0, 0.0, 0.0],
                [+0.5, -0.5, -0.5, +1, 0, 0, 1.0, 0.0],
                [+0.5, -0.5, +0.5, +1, 0, 0, 1.0, 1.0],
                [+0.5, +0.5, +0.5, +1, 0, 0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )
        vertices[:, 0:3] *= [size[0], size[1], size[2]]

        indices = np.array(
            [
                [0, 2, 1],
                [0, 3, 2],
                [4, 6, 5],
                [4, 7, 6],
                [8, 10, 9],
                [8, 11, 10],
                [12, 14, 13],
                [12, 15, 14],
                [16, 18, 17],
                [16, 19, 18],
                [20, 22, 21],
                [20, 23, 22],
            ],
            dtype=np.uint32,
        )

        return Mesh(vertices, indices)

    @classmethod
    def create_sphere(cls, radius: float = 0.5, segments: int = 32, rings: int = 16):
        """Create a UV sphere mesh.
        
        Args:
            radius: Sphere radius
            segments: Number of segments around the sphere (longitude)
            rings: Number of rings from pole to pole (latitude)
        """
        vertices_list = []
        indices_list = []
        
        for ring in range(rings + 1):
            phi = np.pi * ring / rings  # 0 to pi
            for seg in range(segments + 1):
                theta = 2 * np.pi * seg / segments  # 0 to 2*pi
                
                # Position
                x = radius * np.sin(phi) * np.cos(theta)
                y = radius * np.cos(phi)
                z = radius * np.sin(phi) * np.sin(theta)
                
                # Normal (normalized position for unit sphere)
                nx = np.sin(phi) * np.cos(theta)
                ny = np.cos(phi)
                nz = np.sin(phi) * np.sin(theta)
                
                # UV
                u = seg / segments
                v = ring / rings
                
                vertices_list.append([x, y, z, nx, ny, nz, u, v])
        
        # Generate indices
        for ring in range(rings):
            for seg in range(segments):
                current = ring * (segments + 1) + seg
                next_ring = (ring + 1) * (segments + 1) + seg
                
                indices_list.append([current, current + 1, next_ring])
                indices_list.append([current + 1, next_ring + 1, next_ring])
        
        vertices = np.array(vertices_list, dtype=np.float32)
        indices = np.array(indices_list, dtype=np.uint32)
        
        return Mesh(vertices, indices)

    @classmethod
    def create_capsule(cls, radius: float = 0.5, height: float = 1.0, segments: int = 32, rings: int = 8):
        """Create a capsule mesh (cylinder with hemispherical caps).
        
        Args:
            radius: Capsule radius
            height: Height of the cylindrical part (total height = height + 2*radius)
            segments: Number of segments around the capsule
            rings: Number of rings for each hemisphere
        """
        vertices_list = []
        indices_list = []
        half_height = height / 2
        
        # Top hemisphere
        for ring in range(rings + 1):
            phi = (np.pi / 2) * ring / rings
            sin_phi = np.sin(phi)
            cos_phi = np.cos(phi)
            
            for seg in range(segments + 1):
                theta = 2 * np.pi * seg / segments
                sin_theta = np.sin(theta)
                cos_theta = np.cos(theta)
                
                # Position - standard sphere formula, offset up by half_height
                x = radius * sin_phi * cos_theta
                y = half_height + radius * cos_phi
                z = radius * sin_phi * sin_theta
                
                # Normal - same as sphere, pointing outward
                nx = sin_phi * cos_theta
                ny = cos_phi
                nz = sin_phi * sin_theta
                
                u = seg / segments
                v = 0.25 * ring / rings
                
                vertices_list.append([x, y, z, nx, ny, nz, u, v])
        
        top_hemi_vertex_count = (rings + 1) * (segments + 1)
        
        # Cylinder part (2 rings at top and bottom of cylinder)
        for i, cy in enumerate([half_height, -half_height]):
            for seg in range(segments + 1):
                theta = 2 * np.pi * seg / segments
                sin_theta = np.sin(theta)
                cos_theta = np.cos(theta)
                
                x = radius * cos_theta
                y = cy
                z = radius * sin_theta
                
                # Normal - horizontal, pointing outward
                nx = cos_theta
                ny = 0
                nz = sin_theta
                
                u = seg / segments
                v = 0.25 + 0.5 * i
                
                vertices_list.append([x, y, z, nx, ny, nz, u, v])
        
        cylinder_vertex_count = 2 * (segments + 1)
        
        # Bottom hemisphere
        for ring in range(rings + 1):
            phi = (np.pi / 2) + (np.pi / 2) * ring / rings
            sin_phi = np.sin(phi)
            cos_phi = np.cos(phi)
            
            for seg in range(segments + 1):
                theta = 2 * np.pi * seg / segments
                sin_theta = np.sin(theta)
                cos_theta = np.cos(theta)
                
                # Position - standard sphere formula, offset down by half_height
                x = radius * sin_phi * cos_theta
                y = -half_height + radius * cos_phi
                z = radius * sin_phi * sin_theta
                
                # Normal - same as sphere, pointing outward
                nx = sin_phi * cos_theta
                ny = cos_phi
                nz = sin_phi * sin_theta
                
                u = seg / segments
                v = 0.75 + 0.25 * ring / rings
                
                vertices_list.append([x, y, z, nx, ny, nz, u, v])
        
        # Generate indices for top hemisphere
        for ring in range(rings):
            for seg in range(segments):
                current = ring * (segments + 1) + seg
                next_ring = (ring + 1) * (segments + 1) + seg
                indices_list.append([current, current + 1, next_ring])
                indices_list.append([current + 1, next_ring + 1, next_ring])
        
        # Generate indices for cylinder
        cyl_start = top_hemi_vertex_count
        for seg in range(segments):
            top_left = cyl_start + seg
            top_right = cyl_start + seg + 1
            bottom_left = cyl_start + (segments + 1) + seg
            bottom_right = cyl_start + (segments + 1) + seg + 1
            indices_list.append([top_left, top_right, bottom_left])
            indices_list.append([top_right, bottom_right, bottom_left])
        
        # Generate indices for bottom hemisphere
        bot_start = top_hemi_vertex_count + cylinder_vertex_count
        for ring in range(rings):
            for seg in range(segments):
                current = bot_start + ring * (segments + 1) + seg
                next_ring = bot_start + (ring + 1) * (segments + 1) + seg
                indices_list.append([current, current + 1, next_ring])
                indices_list.append([current + 1, next_ring + 1, next_ring])
        
        vertices = np.array(vertices_list, dtype=np.float32)
        indices = np.array(indices_list, dtype=np.uint32)
        
        return Mesh(vertices, indices)
