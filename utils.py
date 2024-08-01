import torch
import numpy as np
from PIL import Image


def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def numpy2pil(image):
    return Image.fromarray(np.clip(255. * image.squeeze(), 0, 255).astype(np.uint8))

def to_pil(image):
    if isinstance(image, Image.Image):
        return image
    if isinstance(image, torch.Tensor):
        return tensor2pil(image)
    if isinstance(image, np.ndarray):
        return numpy2pil(image)
    raise ValueError(f"Cannot convert {type(image)} to PIL.Image")

def has_transparency(image):
    if isinstance(image, Image.Image):
        if image.info.get("transparency", None) is not None:
            return True
        if image.mode == "P":
            transparent = image.info.get("transparency", -1)
            for _, index in image.getcolors():
                if index == transparent:
                    return True
        elif image.mode == "RGBA":
            extrema = image.getextrema()
            if extrema[3][0] < 255:
                return True
    
    if isinstance(image, torch.Tensor) or isinstance(image, np.ndarray):
        return True if image.shape[-1] == 4 else False
        
    return False

def copy_image(image):
    if isinstance(image, torch.Tensor):
        return image.clone().detach()
    return image.copy() # works for both numpy and pil

def get_resized_alpha(image, transparency_mask, upscaling_factor):
    try:
        if transparency_mask is not None:
            if image.shape[:3] != transparency_mask.shape[:3] and len(transparency_mask.shape) != len(image.shape) + 1:
                # Invalid mask. Attempt with original image
                if has_transparency(image):
                    img = copy_image(image)
                else:
                    return None
            else:
                img = transparency_mask
                img = 1.0 - img # invert
                img = img.reshape((-1, 1, img.shape[-2], img.shape[-1])).movedim(1, -1).expand(-1, -1, -1, 3) # mask -> image
        else:
            if has_transparency(image):
                img = copy_image(image)
            else:
                return None
        
        if isinstance(img, torch.Tensor):
            img = img.cpu().numpy()
        if isinstance(img, np.ndarray):
            mode = 'RGBA' if transparency_mask is None else 'RGB'
            img = Image.fromarray(np.clip(255. * img.squeeze(), 0, 255).astype(np.uint8), mode=mode)
            if not img.getbbox(): # some RGB images return fully black masks with the 'Load Image' node - cannot apply masking if so
                return None
        
        resized_alpha = img.resize((img.width * upscaling_factor, img.height * upscaling_factor)).split()[-1]
    except:
        return None
    return resized_alpha

def paste_alpha(image, alpha):
    image = image.convert("RGBA")
    image.putalpha(alpha)
    return image


def prepare_input(image, transparency_mask, reapply_transparency, upscaling_factor):
    resized_alpha = get_resized_alpha(image, transparency_mask, upscaling_factor) if reapply_transparency else None
    image = to_pil(image).convert("RGB")
    return image, resized_alpha

