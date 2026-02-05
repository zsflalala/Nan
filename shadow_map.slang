import scene;
import common;

struct ShadowMapGenerator {
    RWTexture2D<float> shadow_map;
    float4x4 light_view_matrix;
    float4x4 inv_light_view_matrix; // Inverse of Light View (Camera -> World)
    float3 light_direction;
    float ortho_size;
    float near_plane;
    float far_plane;

    void execute(uint2 pixel)
    {
        uint2 dim;
        shadow_map.GetDimensions(dim.x, dim.y);
        
        // 1. Pixel to NDC [-1, 1]
        float2 ndc = (float2(pixel) + 0.5) / float2(dim) * 2.0 - 1.0;
        
        // 2. Ortho Ray Origin in View Space
        float3 origin_view = float3(ndc.x * ortho_size, ndc.y * ortho_size, -near_plane);
        float4 origin_world = mul(inv_light_view_matrix, float4(origin_view, 1.0));
        
        // 3. Ray Direction
        float3 direction = light_direction;
        
        // 4. Trace Ray
        Ray ray;
        ray.origin = origin_world.xyz;
        ray.dir = direction;
        ray.t_min = 0.0; 
        ray.t_max = far_plane - near_plane; 
        
        float t_hit;
        HitInfo hit = g_scene.intersect(ray, t_hit);
        
        // 5. Store Depth
        if (hit.valid)
        {
            float linear_depth = t_hit / (far_plane - near_plane);
            shadow_map[pixel] = linear_depth;
        }
        else
        {
            shadow_map[pixel] = 1.0;
        }
    }
}

[shader("compute")]
[numthreads(8, 8, 1)]
void compute_main(uint3 dispatch_thread_id: SV_DispatchThreadID)
{
    uint2 pixel = dispatch_thread_id.xy;
    uint2 dim;
    g_generator.shadow_map.GetDimensions(dim.x, dim.y);
    if (any(pixel >= dim)) return;
    
    g_generator.execute(pixel);
}

ParameterBlock<ShadowMapGenerator> g_generator;
