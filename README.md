# ComfyUI LoRA Dataset Prep

English | [日本語](README.ja.md)

A ComfyUI custom node that batch processes an image folder to produce images and matching captions for LoRA training. It adjusts the short and long sides of images to specified limits and can use a ComfyUI upscale model (such as RealESRGAN) when needed. Captions are generated from the original images with Qwen3-VL, with the description tailored to the selected training focus.

## Repository structure

```text
ComfyUI-LoRA-Dataset-Prep/
├── __init__.py                 # ComfyUI node registration
├── nodes.py                    # Batch preprocessing and caption generation
├── caption_prompt.py           # Caption instructions by training focus
├── review.py                   # Image and caption review index
├── requirements.txt            # Dependencies installed by Manager
├── pyproject.toml              # Comfy Registry metadata
├── workflows/
│   └── lora_dataset_preparation.json
├── README.md                  # English README
├── README.ja.md               # Japanese README
└── LICENSE
```

## Installation

After the repository is published, you can search for **ComfyUI LoRA Dataset Prep** in ComfyUI Manager and install it. Before it is published to the Registry, clone this repository into `ComfyUI/custom_nodes/` and run `pip install -r requirements.txt` in the same Python environment as ComfyUI. Restart ComfyUI after installation.

To use an upscale model, place a compatible `.pth` model in `ComfyUI/models/upscale_models/`. Models are not included in this repository. The Qwen3-VL model is downloaded from Hugging Face on the first run. Check each model distributor's license and terms of use.

## Usage

1. Drag `workflows/lora_dataset_preparation.json` into the ComfyUI interface to load it.
2. Set `source_folder` to the image folder and `output_folder` to a separate output folder. Relative paths are resolved from the ComfyUI process's working directory.
3. Select the training subject with `training_focus`. Supported values are `auto`, `person`, `object`, `background`, `outfit`, `item`, `pose`, `art_style`, `visual_effect`, `expression`, `camera_angle`, `composition`, `logo`, `symbol`, and `custom`. Use `custom_focus` for additional instructions; it is required when `training_focus` is `custom`.
4. Change `trigger_word` to the term you use for training. The default, `subject`, is an example. Leave it blank to omit the term from captions.
5. In the included workflow, `UpscaleModelLoader` is connected to `upscale_model`. Make sure the selected model is installed. To process images without an upscale model, disconnect it and set `upscale_mode` to `lanczos`.
6. Run the queue, then open `review_index.html` in the output folder in a browser to inspect the images and captions.

The node reads JPG, PNG, WebP, BMP, and TIFF files directly inside the source folder. It produces `filename.png` and `filename.txt` pairs, a `prep_report.csv` processing report, and a `review_index.html` review page. The review page shows every image in the source folder, including skipped pairs and processing failures. Click an image to open its output at full size. Source images are not modified. When `skip_existing` is enabled, an image is skipped if both output files already exist. Captions are always generated from the original image before upscaling.

The caption instructions apply to photographs, illustrations, graphics, and renders, and prioritize the appearance of the selected subject. They ask for logo text only when it is clearly legible. To regenerate existing pairs after changing `training_focus` or `custom_focus`, disable `skip_existing`. If you have manually edited existing captions, back them up before overwriting them.

`min_short_side` is the target for enlarging the short side, and `max_long_side` is the maximum length of the long side. The aspect ratio is preserved, and the long-side limit takes priority. As a result, the short side may not reach its target for extremely tall or wide images. Input images with the same base name, even if their extensions or letter case differ, cause an error. VRAM use and processing time depend on the VLM and image size.

## Publishing to ComfyUI Manager / Registry

The repository is **[magichan-lab/ComfyUI-LoRA-Dataset-Prep](https://github.com/magichan-lab/ComfyUI-LoRA-Dataset-Prep)**. The node identifier is `LoRADatasetPrep`, its display name is `LoRA Dataset Prep (Batch Upscale + Caption)`, and the workflow filename is `lora_dataset_preparation.json`.

1. Create a Publisher in the [Comfy Registry](https://registry.comfy.org/) and replace `PublisherId` in `pyproject.toml` with its actual ID.
2. Create a Registry publishing API key and follow the [official publishing instructions](https://docs.comfy.org/registry/publishing) to publish version `0.1.0` using `comfy node publish` or GitHub Actions.
3. After publishing to the Registry, verify that the node can be found and installed through ComfyUI Manager and that the bundled workflow loads.

The Registry provides search and installation for ComfyUI Manager. Manager's documentation also describes the older `custom-node-list.json` pull request method, but the Registry process is preferred for new publications.

## Limitations

Automatically generated captions can contain mistakes or unwanted descriptions. Review the images and text before training. Check the rights and permitted distribution of any images you use, including images of people.
