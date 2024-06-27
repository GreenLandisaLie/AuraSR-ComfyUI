import os.path
import json
from PIL import Image
import comfy.utils
import folder_paths
from aura_sr import AuraSR


class AuraSRUpscaler:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"model_name": (folder_paths.get_filename_list("aura-sr"), ),
                             "image": ("IMAGE",),
                             "tile_batch_size": ("INT", {"default": 8, "min": 1, "max": 32}),
                             }}
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "main"

    #CATEGORY = "loaders"
    
    def __init__(self):
        self.loaded = False
        self.model_name = ""
        self.aura_sr = None
    
    
    def unload(): # I don't know if this is the best way to unload a model but it should work
        self.aura_sr.upsampler = None
        self.aura_sr = None
        self.loaded = False
        self.model_name = ""
    
    
    def load(model_name):
        model_path = folder_paths.get_full_path("aura-sr", model_name)
        config_path = model_path[:model_path.rindex('.')] + ".json"
        config_path = config_path if os.path.isfile(config_path) else model_path.replace(model_name, "config.json")
        
        device = model_management.get_torch_device()
        config = json.loads(config_path.read_text())
        
        checkpoint = comfy.utils.load_torch_file(model_path, safe_load=True)
        
        self.aura_sr = AuraSR(config=config, device=device)
        self.aura_sr.upsampler.load_state_dict(checkpoint, strict=True)
        
        self.loaded = True
        self.model_name = model_name
    
    
    def main(self, model_name, image, tile_batch_size):
        if not self.loaded or self.model_name != model_name:
            self.unload()
            self.load(model_name)
        else:
            device = model_management.get_torch_device()
            self.aura_sr.upsampler.to(device)
            
        upscaled_image = self.aura_sr.upscale_4x(image)
        
        self.aura_sr.upsampler.to("cpu")
        
        return (upscaled_image, )




NODE_CLASS_MAPPINGS = {
    "AuraSR.AuraSRUpscaler": AuraSRUpscaler
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AuraSR.AuraSRUpscaler": "AuraSR Upscaler"
}
