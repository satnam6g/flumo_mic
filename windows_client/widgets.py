import customtkinter as ctk
import tkinter as tk
from theme import Colors, Fonts
from PIL import Image, ImageDraw

def create_gradient_image(width, height, color1, color2):
    """Creates a horizontal linear gradient image using Pillow."""
    image = Image.new("RGBA", (width, height), color1)
    draw = ImageDraw.Draw(image)
    
    # Simple linear interpolation
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    
    for x in range(width):
        r = int(r1 + (r2 - r1) * x / width)
        g = int(g1 + (g2 - g1) * x / width)
        b = int(b1 + (b2 - b1) * x / width)
        draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))
        
    return image

class AudioMeter(ctk.CTkFrame):
    def __init__(self, master, width=400, height=40, **kwargs):
        super().__init__(master, width=width, height=height, fg_color=Colors.SURFACE_ELEVATED, corner_radius=8, **kwargs)
        self.width = width
        self.height = height
        self.level = 0.0 # 0.0 to 1.0
        
        self.canvas = tk.Canvas(self, width=width, height=height, bg=Colors.SURFACE_ELEVATED, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Pre-render the gradient image
        self.grad_img = create_gradient_image(width, height, Colors.PRIMARY, Colors.SECONDARY)
        import os
        from PIL import ImageTk
        self.grad_photo = ImageTk.PhotoImage(self.grad_img)
        
        # Draw gradient but mask it
        self.grad_id = self.canvas.create_image(0, 0, image=self.grad_photo, anchor="nw")
        
        # Mask overlay (blocks the gradient where level < max)
        self.mask_id = self.canvas.create_rectangle(0, 0, width, height, fill=Colors.SURFACE_ELEVATED, outline="")
        
        # Peak indicator
        self.peak_id = self.canvas.create_line(0, 0, 0, height, fill=Colors.ERROR, width=2, state="hidden")
        self.peak_level = 0.0
        self.peak_timer = 0
        
        # Make rounded corners on canvas by overlaying shapes (simplified: just rely on frame's border, or accept slight square edges on the inside)
        # We will use simple rectangle masking
        
    def set_level(self, level):
        self.level = max(0.0, min(1.0, level))
        fill_width = int(self.width * self.level)
        
        # Move the mask to reveal the gradient up to fill_width
        self.canvas.coords(self.mask_id, fill_width, 0, self.width, self.height)
        
        # Update peak
        if self.level > self.peak_level:
            self.peak_level = self.level
            self.peak_timer = 20 # frames to hold peak
        
        if self.peak_timer > 0:
            peak_x = int(self.width * self.peak_level)
            self.canvas.coords(self.peak_id, peak_x, 0, peak_x, self.height)
            self.canvas.itemconfig(self.peak_id, state="normal")
            self.peak_timer -= 1
        else:
            self.peak_level -= 0.05 # decay peak
            if self.peak_level <= 0:
                self.peak_level = 0
                self.canvas.itemconfig(self.peak_id, state="hidden")

class GradientButton(ctk.CTkButton):
    def __init__(self, master, color1, color2, text="", **kwargs):
        # Create a gradient image for the button
        w, h = 200, 40 # default
        img = create_gradient_image(w, h, color1, color2)
        self.ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
        
        super().__init__(
            master, 
            text=text, 
            image=self.ctk_img, 
            compound="center",
            fg_color="transparent",
            hover_color=color2, # fallback hover
            text_color="white",
            font=Fonts.button(),
            **kwargs
        )

class StatusLED(ctk.CTkCanvas):
    def __init__(self, master, size=16, color=Colors.ERROR, **kwargs):
        super().__init__(master, width=size, height=size, bg=Colors.SURFACE, highlightthickness=0, **kwargs)
        self.size = size
        self.color = color
        self.oval = self.create_oval(2, 2, size-2, size-2, fill=color, outline="")
        self.pulse_timer = None
        self.is_pulsing = False
        
    def set_color(self, color):
        self.color = color
        self.itemconfig(self.oval, fill=color)
        
    def pulse(self, state=True):
        self.is_pulsing = state
        if state:
            self._do_pulse()
            
    def _do_pulse(self, bright=True):
        if not self.is_pulsing:
            self.itemconfig(self.oval, fill=self.color)
            return
            
        # Swap between full color and dimmed color
        current_fill = self.color if bright else Colors.SURFACE_ELEVATED
        self.itemconfig(self.oval, fill=current_fill)
        self.pulse_timer = self.after(500, self._do_pulse, not bright)
