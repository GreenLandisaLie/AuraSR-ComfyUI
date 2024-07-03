import os
from pathlib import Path
import json
import folder_paths
from comfy import model_management
import comfy.utils
from .aura_sr import AuraSR
from .utils import *


aurasr_folders = [p for p in os.listdir(folder_paths.models_dir) if os.path.isdir(os.path.join(folder_paths.models_dir, p)) and (p.lower() == "aura-sr" or p.lower() == "aurasr" or p.lower() == "aura_sr")]
aurasr_fullpath = os.path.join(folder_paths.models_dir, aurasr_folders[0]) if len(aurasr_folders) > 0 else os.path.join(folder_paths.models_dir, "Aura-SR")
if not os.path.isdir(aurasr_fullpath):
    os.mkdir(aurasr_fullpath)

folder_paths.folder_names_and_paths["aura-sr"] = ([aurasr_fullpath], folder_paths.supported_pt_extensions)

AuraSRUpscalers = []

def getAuraClassFromMemory(model_name):
    i = 0
    while (i < len(AuraSRUpscalers)):
        if model_name == AuraSRUpscalers[i].model_name:
            if not AuraSRUpscalers[i].loaded: # remove if model not loaded
                AuraSRUpscalers[i].unload()
                AuraSRUpscalers.pop(i)
            else:
                return AuraSRUpscalers[i]
        i += 1
    return None


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
        self.config = None
        self.device = "cpu"
    
    
    def unload(self):
        if self.aura_sr is not None:
            self.aura_sr.upsampler = None  # I don't know if this is the best way to unload a model but it should work
        self.aura_sr = None
        self.loaded = False
        self.model_name = ""
        self.upscaling_factor = 4
        self.config = None
        self.device = "cpu"
    
    
    def load(self, model_name, device):
        model_path = folder_paths.get_full_path("aura-sr", model_name)
        config_path = model_path[:model_path.rindex('.')] + ".json"
        config_path = config_path if os.path.isfile(config_path) else model_path.replace(model_name, "config.json")
        
        if os.path.isfile(config_path):
            self.config = json.loads(Path(config_path).read_text())
        else:
            return
        
        try:
            self.upscaling_factor = int(self.config["image_size"] / self.config["input_image_size"])
        except:
            print(f"[AuraSR-ComfyUI] Failed to calculate {model_name}'s upscaling factor. Defaulting to 4.")
            self.upscaling_factor = 4
        
        checkpoint = comfy.utils.load_torch_file(model_path, safe_load=True)
        
        self.aura_sr = AuraSR(config=self.config, device=device)
        self.aura_sr.upsampler.load_state_dict(checkpoint, strict=True)
        
        self.loaded = True
        self.model_name = model_name
        self.device = device
    
    
    def load_from_memory(self, cl, device):
        self.loaded = True
        self.model_name = cl.model_name
        self.aura_sr = cl.aura_sr
        self.upscaling_factor = cl.upscaling_factor
        self.device_warned = cl.device_warned
        self.config = cl.config
        if device != cl.device:
            self.aura_sr.upsampler.to(device)
            cl.device = device
        self.device = device
    
    
    
    def main(self, model_name, image, reapply_transparency, tile_batch_size, device, offload_to_cpu, transparency_mask=None):
        
        # set device
        torch_device = model_management.get_torch_device()
        if model_management.directml_enabled:
            device = "cpu"
            if device == "default" and not self.device_warned:
                print("[AuraSR-ComfyUI] Cannot run AuraSR on DirectML device. Using CPU instead (this will be VERY SLOW!)")
                self.device_warned = True
        else:
            device = torch_device if device == "default" else "cpu"
            device = device if str(device).lower() != "cpu" else "cpu" # force device to be "cpu" when using CPU in default mode
        
        # load/unload model
        class_in_memory = getAuraClassFromMemory(model_name)
        if not self.loaded or self.model_name != model_name:
            
            if class_in_memory is None:
                self.unload()
                self.load(model_name, device)
                AuraSRUpscalers.append(self)
            else:
                self.load_from_memory(class_in_memory, device)
            
            if self.config is None:
                print("[AuraSR-ComfyUI] Could not find a config/ModelName .json file! Please download it from the model's HF page and place it inside '\models\Aura-SR'.\nReturning original image.")
                return (image, )
        else:
            if self.device != device:
                self.aura_sr.upsampler.to(device)
                self.device = device
                if class_in_memory is not None:
                    class_in_memory.device = device
        
        # prepare input image and resized_alpha
        image, resized_alpha = prepare_input(image, transparency_mask, reapply_transparency, self.upscaling_factor)
        
        # upscale
        try:
            upscaled_image = self.aura_sr.upscale_4x(image=image, max_batch_size=tile_batch_size)
        except:
            print("[AuraSR-ComfyUI] Failed to upscale with AuraSR. Returning original image.")
            upscaled_image = image
        
        # apply resized_alpha
        if reapply_transparency and resized_alpha is not None:
            try:
                upscaled_image = paste_alpha(upscaled_image, resized_alpha)
            except:
                print("[AuraSR-ComfyUI] Failed to apply alpha layer.")
        
        # back to tensor
        upscaled_image = pil2tensor(upscaled_image)
        
        # offload to cpu
        if offload_to_cpu:
            self.aura_sr.upsampler.to("cpu")
            self.device = "cpu"
            if class_in_memory is not None:
                class_in_memory.device = "cpu"
        
        return (upscaled_image, )




NODE_CLASS_MAPPINGS = {
    "AuraSR.AuraSRUpscaler": AuraSRUpscaler
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AuraSR.AuraSRUpscaler": "AuraSR Upscaler"
}
