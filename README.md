# AuraSR-ComfyUI
Very basic ComfyUI implementation of [Aura-SR](https://github.com/fal-ai/aura-sr)

![Interface](nodes_preview/pv1.png)

Instructions:
- Create a folder named 'Aura-SR' inside '\models'.
- Download the .safetensors AND config.json files from [HuggingFace](https://huggingface.co/fal/AuraSR/tree/main) and place them in '\models\Aura-SR'
- (Optional) Rename the model to whatever you want and rename the config file to the same name as the model (this allows for future, multiple models with their own unique configs).
- Using ComfyUI Manager install via Git URL, restart then reload the browser's page.
- Add Node > AuraSR > AuraSR Upscaler
- All of the node's parameters are self explanatory apart for 'transparency_mask' and 'reapply_transparency':
  - transparency_mask: (Optional) A mask obtained from loading a RGBA image (with transparent pixels). Can be directly connected to the 'Load Image' native node.
  - reapply_transparency: When given a valid mask AND/OR a RGBA image - it will attempt to reapply the transparency of the original image to the upscaled one. Keep in mind that the 'Load Image' native node auto-converts the input image to RGB (no transparency) before sending it to another node. Therefore if you are not passing a valid 'transparency_mask' then you need a specialized node capable of loading and outputing in RGBA mode.


 
Notes:

I'm not a dev (just self taught as an hobby) and have little to no experience with image transformation in Python. Everything seems to be working at first glance but I don't trust myself to confidently say there are no flaws. Additionally, this code hasn't been tested on a CUDA device yet (I'm on AMD) but it should work.

TODO:
- Add support for multiple image inputs
- Add missing safety checks against invalid inputs
