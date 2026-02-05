# Scene Selector UI
# 场景选择器窗口

import slangpy as spy
from scene_config import SceneConfig, SceneType, SHADOW_MAP_SIZES, DEFAULT_SHADOW_MAP_SIZE
from typing import Optional, Callable, List


class SceneSelector:
    """
    启动时的场景选择器窗口。
    在程序启动时显示，让用户选择要加载的场景。
    """
    
    def __init__(self, device: spy.Device, window: spy.Window, surface: spy.Surface):
        self.device = device
        self.window = window
        self.surface = surface
        self.ui_context = spy.ui.Context(device)
        self.selected_scene: Optional[SceneConfig] = None
        self.should_load = False
        self.available_scenes = SceneConfig.get_available_scenes()
        self.current_selection = 0
        
        # Shadow map size selection
        self.shadow_map_sizes = SHADOW_MAP_SIZES
        self.current_shadow_map_index = self.shadow_map_sizes.index(DEFAULT_SHADOW_MAP_SIZE)
        
        # UI elements - created once
        self._create_ui()
        
        # Bind event handlers for UI interaction
        self.window.on_mouse_event = self._on_mouse_event
        self.window.on_keyboard_event = self._on_keyboard_event
    
    def _on_mouse_event(self, event: spy.MouseEvent):
        """Handle mouse events for UI."""
        self.ui_context.handle_mouse_event(event)
    
    def _on_keyboard_event(self, event: spy.KeyboardEvent):
        """Handle keyboard events for UI."""
        self.ui_context.handle_keyboard_event(event)
        # Allow ESC to close
        if event.type == spy.KeyboardEventType.key_press:
            if event.key == spy.KeyCode.escape:
                self.window.close()
    
    def _create_ui(self):
        """Create the scene selector UI widgets once."""
        # Calculate window position (centered)
        win_width = 400
        win_height = 300
        pos_x = max(0, (self.window.width - win_width) / 2)
        pos_y = max(0, (self.window.height - win_height) / 2)
        
        self.ui_window = spy.ui.Window(
            self.ui_context.screen, 
            "Select Scene", 
            spy.float2(pos_x, pos_y), 
            spy.float2(win_width, win_height)
        )
        
        # Create checkboxes for each scene
        self.scene_buttons: List[spy.ui.CheckBox] = []
        for i, scene in enumerate(self.available_scenes):
            button = spy.ui.CheckBox(self.ui_window, f"{scene.name}")
            self.scene_buttons.append(button)
            # Set the current selection as checked
            button.value = (i == self.current_selection)
        
        # Shadow map size selection
        self.shadow_map_buttons: List[spy.ui.CheckBox] = []
        for i, size in enumerate(self.shadow_map_sizes):
            button = spy.ui.CheckBox(self.ui_window, f"Shadow Map: {size}x{size}")
            self.shadow_map_buttons.append(button)
            button.value = (i == self.current_shadow_map_index)
        
        # Load button with callback
        self.load_button = spy.ui.Button(
            self.ui_window, 
            "Load Scene",
            callback=self._on_load_clicked
        )
    
    def _on_load_clicked(self):
        """Callback when load button is clicked."""
        if self.available_scenes:
            self.selected_scene = self.available_scenes[self.current_selection]
            # Set the selected shadow map size
            self.selected_scene.shadow_map_size = self.shadow_map_sizes[self.current_shadow_map_index]
            self.should_load = True
    
    def update(self) -> bool:
        """
        Update the selector state based on UI interactions.
        Returns True if user clicked load button.
        """
        # Process scene radio button behavior (only one can be selected)
        if self.scene_buttons:
            new_selection = -1
            for i, button in enumerate(self.scene_buttons):
                if button.value and i != self.current_selection:
                    new_selection = i
                    break
            
            if new_selection >= 0:
                self.current_selection = new_selection
                for i, button in enumerate(self.scene_buttons):
                    button.value = (i == self.current_selection)
            else:
                self.scene_buttons[self.current_selection].value = True
        
        # Process shadow map size radio button behavior
        if self.shadow_map_buttons:
            new_shadow_selection = -1
            for i, button in enumerate(self.shadow_map_buttons):
                if button.value and i != self.current_shadow_map_index:
                    new_shadow_selection = i
                    break
            
            if new_shadow_selection >= 0:
                self.current_shadow_map_index = new_shadow_selection
                for i, button in enumerate(self.shadow_map_buttons):
                    button.value = (i == self.current_shadow_map_index)
            else:
                self.shadow_map_buttons[self.current_shadow_map_index].value = True
        
        return self.should_load
    
    def render(self) -> bool:
        """
        Render the selector UI.
        Returns False if surface is not ready.
        """
        # Check if surface is configured
        if not self.surface.config:
            return False
        
        # Acquire the next image from the surface
        surface_texture = self.surface.acquire_next_image()
        if not surface_texture:
            return False
        
        command_encoder = self.device.create_command_encoder()
        
        # Render UI
        self.ui_context.begin_frame(surface_texture.width, surface_texture.height)
        self.ui_context.end_frame(surface_texture, command_encoder)
        
        self.device.submit_command_buffer(command_encoder.finish())
        del command_encoder
        del surface_texture
        
        self.surface.present()
        return True
    
    def get_selected_scene(self) -> Optional[SceneConfig]:
        """Get the selected scene config."""
        return self.selected_scene
    
    def run_selection_loop(self) -> Optional[SceneConfig]:
        """
        Run the selection loop until user makes a choice.
        Returns the selected SceneConfig, or None if window closed.
        """
        print(f"[SceneSelector] Starting selection loop with {len(self.available_scenes)} scenes")
        while not self.window.should_close():
            self.window.process_events()
            
            # Check for updates first
            if self.update():
                print(f"[SceneSelector] Scene selected: {self.selected_scene.name if self.selected_scene else 'None'}")
                break
            
            # Render
            self.render()
        
        return self.selected_scene
