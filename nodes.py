import os
from pathlib import Path
import json
import folder_paths
from comfy import model_management
import comfy.utils
from .aura_sr import AuraSR
from .utils import *


folder_paths.folder_names_and_paths["aura-sr"] = ([os.path.join(folder_paths.models_dir, "aura-sr")], folder_paths.supported_pt_extensions)

class AuraSRUpscaler:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"model_name": (folder_paths.get_filename_list("aura-sr"),),
                             "image": ("IMAGE",),
                             "reapply_transparency": ("BOOLEAN", {"default": True}),
                             "tile_batch_size": ("INT", {"default": 8, "min": 1, "max": 32}),
                             "device": (["default", "cpu"],),
                             "offload_to_cpu": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "transparency_mask": ("MASK",),
            },
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "main"

    CATEGORY = "AuraSR"
    
    def __init__(self):
        self.loaded = False
        self.model_name = ""
        self.aura_sr = None
        self.upscaling_factor = 4
        self.device_warned = False
    
    
    def unload(self):
        if self.aura_sr is not None:
            self.aura_sr.upsampler = None  # I don't know if this is the best way to unload a model but it should work
        self.aura_sr = None
        self.loaded = False
        self.model_name = ""
        self.upscaling_factor = 4
    
    
    def load(self, model_name, device):
        model_path = folder_paths.get_full_path("aura-sr", model_name)
        config_path = model_path[:model_path.rindex('.')] + ".json"
        config_path = config_path if os.path.isfile(config_path) else model_path.replace(model_name, "config.json")
        
        config = json.loads(Path(config_path).read_text())
        
        try:
            self.upscaling_factor = int(config["image_size"] / config["input_image_size"])
        except:
            print(f"Failed to calculate {model_name}'s upscaling factor. Defaulting to 4.")
            self.upscaling_factor = 4
        
        checkpoint = comfy.utils.load_torch_file(model_path, safe_load=True)
        
        self.aura_sr = AuraSR(config=config, device=device)
        self.aura_sr.upsampler.load_state_dict(checkpoint, strict=True)
        
        self.loaded = True
        self.model_name = model_name
    
    
    def main(self, model_name, image, reapply_transparency, tile_batch_size, device, offload_to_cpu, transparency_mask=None):
        torch_device = model_management.get_torch_device()
        if model_management.directml_enabled and device == "default":
            device = "cpu"
            if not self.device_warned:
                print("Cannot run AuraSR on DirectML device. Using CPU instead (this will be VERY SLOW!)")
                self.device_warned = True
        else:
            device = torch_device
        
        if not self.loaded or self.model_name != model_name:
            self.unload()
            self.load(model_name, device)
        else:
            self.aura_sr.upsampler.to(device)
        
        image, resized_alpha = prepare_input(image, transparency_mask, reapply_transparency, self.upscaling_factor)        
        
        try:
            upscaled_image = self.aura_sr.upscale_4x(image=image, max_batch_size=tile_batch_size)
        except:
            print("Failed to upscale with AuraSR. Returning original image.")
            upscaled_image = image
        
        if reapply_transparency and resized_alpha is not None:
            try:
                upscaled_image = paste_alpha(upscaled_image, resized_alpha)
            except:
                print("Failed to apply alpha layer.")
        
        upscaled_image = pil2tensor(upscaled_image)
        
        if offload_to_cpu:
            self.aura_sr.upsampler.to("cpu")
        
        return (upscaled_image, )




NODE_CLASS_MAPPINGS = {
    "AuraSR.AuraSRUpscaler": AuraSRUpscaler
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AuraSR.AuraSRUpscaler": "AuraSR Upscaler"
}
