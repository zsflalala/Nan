import scene;
import common;

struct ShadowMapGenerator {
    RWTexture2D<float> shadow_map;
    float4x4 light_view_proj;
    float4x4 inv_light_view_proj;

    void execute(uint2 pixel)
    {
        uint2 dim;
        shadow_map.GetDimensions(dim.x, dim.y);
        
        float2 param = (float2(pixel) + 0.5) / float2(dim);
        float2 ndc = param * 2.0 - 1.0;
        
        float4 ndc_near = float4(ndc, 0.0, 1.0);
        float4 ndc_far = float4(ndc, 1.0, 1.0);
        
        float4 world_near = mul(inv_light_view_proj, ndc_near);
        float4 world_far = mul(inv_light_view_proj, ndc_far);
        
        float3 origin = world_near.xyz / world_near.w;
        float3 target = world_far.xyz / world_far.w;
        float3 direction = normalize(target - origin);
        
        Ray ray;
        ray.origin = origin;
        ray.dir = direction;
        ray.t_min = 1e-3;
        ray.t_max = 1e4;
        
        float t_hit;
        HitInfo hit = g_scene.intersect(ray, t_hit);
        
        float depth = 1.0;
        if (hit.valid) {
            float3 hit_pos = origin + direction * t_hit;
            float4 clip_pos = mul(light_view_proj, float4(hit_pos, 1.0));
            depth = clip_pos.z / clip_pos.w;
        }
        
        shadow_map[pixel] = depth;
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
