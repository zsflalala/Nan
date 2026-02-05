/**
 * Debug Visualizer Shader
 * Renders wireframe overlays for debug visualization.
 * Uses ray-line distance testing to draw edges on screen.
 */

import common;
import camera;

// Debug visualization parameters
struct DebugParams
{
    RWTexture2D<float4> output;
    uint edge_count;
    StructuredBuffer<float3> edge_buffer;  // Pairs of (start, end) points
    float3 camera_pos;
    float4x4 inv_view_proj;
    float3 line_color;
    float line_thickness;
    uint image_width;
    uint image_height;
};

ParameterBlock<DebugParams> g_debug;

// Shadow map preview parameters
struct PreviewParams
{
    RWTexture2D<float4> output;
    Texture2D<float> shadow_map;
    uint preview_x;
    uint preview_y;
    uint preview_size;
    uint image_width;
    uint image_height;
};

ParameterBlock<PreviewParams> g_preview;

/**
 * Compute the minimum distance from a ray to a line segment.
 * 
 * @param ray_origin    Origin of the ray
 * @param ray_dir       Normalized direction of the ray
 * @param line_start    Start point of the line segment
 * @param line_end      End point of the line segment
 * @param out_t         Parameter along ray where closest point occurs
 * @return              Minimum distance between ray and line segment
 */
float ray_line_distance(
    float3 ray_origin,
    float3 ray_dir,
    float3 line_start,
    float3 line_end,
    out float out_t
)
{
    float3 line_dir = line_end - line_start;
    float line_len = length(line_dir);
    
    if (line_len < 1e-6)
    {
        // Degenerate line segment (point)
        float3 to_point = line_start - ray_origin;
        out_t = dot(to_point, ray_dir);
        float3 closest_on_ray = ray_origin + ray_dir * max(0, out_t);
        return length(line_start - closest_on_ray);
    }
    
    line_dir /= line_len;  // Normalize
    
    // Solve for closest points between ray and line
    // Using the formula for closest approach of two lines
    float3 w0 = ray_origin - line_start;
    float a = 1.0;  // dot(ray_dir, ray_dir) = 1 (normalized)
    float b = dot(ray_dir, line_dir);
    float c = dot(line_dir, line_dir);  // = 1 (normalized)
    float d = dot(ray_dir, w0);
    float e = dot(line_dir, w0);
    
    float denom = a * c - b * b;
    
    float s, t;  // Parameters along ray and line
    
    if (abs(denom) < 1e-6)
    {
        // Lines are parallel
        s = 0;
        t = d / b;  // or use e/c
    }
    else
    {
        s = (b * e - c * d) / denom;
        t = (a * e - b * d) / denom;
    }
    
    // Clamp t to line segment [0, line_len]
    t = clamp(t, 0, line_len);
    
    // Ensure s >= 0 (ray not behind origin)
    s = max(0, s);
    
    // Compute closest points
    float3 closest_on_ray = ray_origin + ray_dir * s;
    float3 closest_on_line = line_start + line_dir * t;
    
    out_t = s;
    return length(closest_on_line - closest_on_ray);
}

/**
 * Generate a camera ray from screen coordinates.
 */
Ray generate_camera_ray(uint2 pixel, uint2 screen_size, float3 camera_pos, float4x4 inv_view_proj)
{
    // Convert pixel to NDC [-1, 1]
    float2 uv = (float2(pixel) + 0.5) / float2(screen_size);
    float2 ndc = uv * 2.0 - 1.0;
    ndc.y = -ndc.y;  // Flip Y for screen coordinates
    
    // Unproject to world space
    float4 near_point = mul(inv_view_proj, float4(ndc, 0.0, 1.0));
    float4 far_point = mul(inv_view_proj, float4(ndc, 1.0, 1.0));
    
    near_point /= near_point.w;
    far_point /= far_point.w;
    
    float3 ray_origin = near_point.xyz;
    float3 ray_dir = normalize(far_point.xyz - near_point.xyz);
    
    return Ray(ray_origin, ray_dir);
}

[shader("compute")]
[numthreads(8, 8, 1)]
void compute_main(uint3 dispatch_id: SV_DispatchThreadID)
{
    uint2 pixel = dispatch_id.xy;
    
    if (pixel.x >= g_debug.image_width || pixel.y >= g_debug.image_height)
        return;
    
    // Generate camera ray for this pixel
    Ray ray = generate_camera_ray(
        pixel,
        uint2(g_debug.image_width, g_debug.image_height),
        g_debug.camera_pos,
        g_debug.inv_view_proj
    );
    
    // Find minimum distance to any edge
    float min_distance = 1e10;
    float min_t = 1e10;
    
    for (uint i = 0; i < g_debug.edge_count; i++)
    {
        // Each edge has 2 points (start, end)
        float3 line_start = g_debug.edge_buffer[i * 2 + 0];
        float3 line_end = g_debug.edge_buffer[i * 2 + 1];
        
        float t;
        float dist = ray_line_distance(ray.origin, ray.dir, line_start, line_end, t);
        
        if (dist < min_distance && t > 0.1)  // Ignore very close intersections
        {
            min_distance = dist;
            min_t = t;
        }
    }
    
    // Convert world-space distance to screen-space thickness
    // Lines further away should appear thinner
    float screen_thickness = g_debug.line_thickness / max(1.0, min_t * 0.1);
    
    // Compute line intensity with anti-aliasing
    float threshold = screen_thickness * 0.01;  // Thickness in world units
    float aa_width = threshold * 0.5;
    
    if (min_distance < threshold + aa_width)
    {
        float4 current_color = g_debug.output[pixel];
        
        // Smooth edge using smoothstep for anti-aliasing
        float alpha = 1.0 - smoothstep(threshold - aa_width, threshold + aa_width, min_distance);
        
        // Blend line color with existing color
        float3 blended = lerp(current_color.rgb, g_debug.line_color, alpha);
        g_debug.output[pixel] = float4(blended, current_color.a);
    }
}

/**
 * Shadow Map Preview Shader
 * Renders the shadow map texture as a preview in the corner of the screen.
 */
[shader("compute")]
[numthreads(8, 8, 1)]
void shadow_map_preview_main(uint3 dispatch_id: SV_DispatchThreadID)
{
    uint2 local_pixel = dispatch_id.xy;
    
    if (local_pixel.x >= g_preview.preview_size || local_pixel.y >= g_preview.preview_size)
        return;
    
    // Calculate screen pixel position
    uint2 screen_pixel = uint2(
        g_preview.preview_x + local_pixel.x,
        g_preview.preview_y + local_pixel.y
    );
    
    // Bounds check
    if (screen_pixel.x >= g_preview.image_width || screen_pixel.y >= g_preview.image_height)
        return;
    
    // Sample shadow map using UV coordinates
    float2 uv = float2(local_pixel) / float2(g_preview.preview_size);
    
    // Get shadow map dimensions
    uint2 shadow_map_size;
    g_preview.shadow_map.GetDimensions(shadow_map_size.x, shadow_map_size.y);
    
    // Sample shadow map
    uint2 shadow_pixel = uint2(uv * float2(shadow_map_size));
    float depth = g_preview.shadow_map[shadow_pixel];
    
    // Visualize depth as grayscale (normalize to visible range)
    float normalized_depth = saturate(depth);  // Assuming depth is already in [0, 1]
    float3 color = float3(normalized_depth, normalized_depth, normalized_depth);
    
    // Draw border
    bool is_border = local_pixel.x == 0 || local_pixel.y == 0 || 
                     local_pixel.x == g_preview.preview_size - 1 || 
                     local_pixel.y == g_preview.preview_size - 1;
    
    if (is_border)
    {
        color = float3(1.0, 0.8, 0.0);  // Yellow border
    }
    
    g_preview.output[screen_pixel] = float4(color, 1.0);
}
