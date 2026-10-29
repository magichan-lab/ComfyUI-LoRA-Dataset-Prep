"""Prepare image and caption pairs for LoRA training in ComfyUI."""
import csv
import gc
import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch

from .caption_prompt import FOCUS_HINTS, build_caption_instruction, format_caption
from .review import write_review_index

LOG = logging.getLogger('LoRADatasetPrep')
EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}


class LoRADatasetPrep:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'source_folder': ('STRING', {'default': 'input/lora_dataset'}),
                'output_folder': ('STRING', {'default': 'output/lora_dataset'}),
                'trigger_word': ('STRING', {'default': 'subject'}),
                'vlm_model_id': ('STRING', {'default': 'Qwen/Qwen3-VL-4B-Instruct'}),
                'min_short_side': ('INT', {'default': 768, 'min': 128, 'max': 2048, 'step': 64}),
                'max_long_side': ('INT', {'default': 1536, 'min': 256, 'max': 4096, 'step': 64}),
                'upscale_mode': (['lanczos', 'upscale_model'],),
                'max_new_tokens': ('INT', {'default': 130, 'min': 32, 'max': 512}),
                'skip_existing': ('BOOLEAN', {'default': True}),
                'run_id': ('INT', {'default': 0, 'min': 0, 'max': 999999999}),
            },
            'optional': {
                'upscale_model': ('UPSCALE_MODEL',),
                'training_focus': (list(FOCUS_HINTS),),
                'custom_focus': ('STRING', {'default': ''}),
            },
        }

    RETURN_TYPES = ('STRING', 'INT', 'INT')
    RETURN_NAMES = ('summary', 'processed', 'skipped')
    FUNCTION = 'execute'
    CATEGORY = 'LoRA Dataset Prep'
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Explicitly rerunnable; skip_existing handles resume safely.
        return float('nan')

    def _load_vlm(self, model_id):
        try:
            from transformers import AutoProcessor, AutoModelForImageTextToText
        except ImportError as exc:
            raise RuntimeError('Install requirements.txt in the ComfyUI Python environment and restart.') from exc
        processor = AutoProcessor.from_pretrained(model_id)
        # Keep the model on GPU when available; CPU is much slower.
        dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16 if torch.cuda.is_available() else torch.float32
        model = AutoModelForImageTextToText.from_pretrained(
            model_id, torch_dtype=dtype, device_map='auto', low_cpu_mem_usage=True
        ).eval()
        return processor, model

    def _caption(self, image, processor, model, trigger, max_new_tokens,
                 training_focus, custom_focus):
        instruction = build_caption_instruction(training_focus, custom_focus)
        messages = [{'role': 'user', 'content': [
            {'type': 'image', 'image': image},
            {'type': 'text', 'text': instruction},
        ]}]
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_dict=True,
            return_tensors='pt'
        )
        device = next(model.parameters()).device
        inputs = {k: v.to(device) if hasattr(v, 'to') else v for k, v in inputs.items()}
        with torch.inference_mode():
            ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        input_len = inputs['input_ids'].shape[-1]
        text = processor.batch_decode(ids[:, input_len:], skip_special_tokens=True)[0]
        return format_caption(trigger, text)

    def _resize(self, image, min_short_side, max_long_side, upscale_mode, upscale_model):
        width, height = image.size
        short, long = min(width, height), max(width, height)
        # Preserve aspect ratio; cap long dimension even when small edge is below target.
        factor = min(min_short_side / short, max_long_side / long) if short < min_short_side else min(1.0, max_long_side / long)
        if factor > 1.0001 and upscale_mode == 'upscale_model':
            if upscale_model is None:
                raise ValueError('upscale_mode=upscale_model requires an UPSCALE_MODEL connection.')
            from comfy_extras.nodes_upscale_model import ImageUpscaleWithModel
            rgb = np.asarray(image.convert('RGB'), dtype=np.float32) / 255.0
            tensor = torch.from_numpy(rgb)[None, ...]
            out, = ImageUpscaleWithModel().upscale(upscale_model, tensor)
            array = (out[0].cpu().numpy().clip(0, 1) * 255).round().astype(np.uint8)
            image = Image.fromarray(array, 'RGB')
            # Downsample any overshoot to intended scale.
            expected = (max(1, round(width * factor)), max(1, round(height * factor)))
            image = image.resize(expected, Image.Resampling.LANCZOS)
            del tensor, out
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        elif abs(factor - 1.0) > 0.0001:
            expected = (max(1, round(width * factor)), max(1, round(height * factor)))
            image = image.resize(expected, Image.Resampling.LANCZOS)
        return image

    def execute(self, source_folder, output_folder, trigger_word, vlm_model_id,
                min_short_side, max_long_side, upscale_mode, max_new_tokens,
                skip_existing, run_id, upscale_model=None, training_focus='auto',
                custom_focus=''):
        src, dest = Path(source_folder).expanduser().resolve(), Path(output_folder).expanduser().resolve()
        if not src.is_dir():
            raise FileNotFoundError(f'Source folder not found: {src}')
        build_caption_instruction(training_focus, custom_focus)
        if dest == src:
            raise ValueError('Use a separate output folder to protect original images.')
        files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in EXTS)
        if not files:
            raise ValueError(f'No images found in: {src}')
        dest.mkdir(parents=True, exist_ok=True)
        # Check filename-stem collisions (e.g. image.jpg and image.png).
        stems = [p.stem.casefold() for p in files]
        if len(stems) != len(set(stems)):
            raise ValueError('Input images include duplicate stems. Rename files first.')
        pending = [p for p in files if not (skip_existing and (dest / f'{p.stem}.png').exists() and (dest / f'{p.stem}.txt').exists())]
        if not pending:
            index = write_review_index(dest, files, [])
            return (f'All {len(files)} images already have image/text output pairs in {dest}. Review: {index}', 0, len(files))
        processor = model = None
        processed, skipped = 0, len(files) - len(pending)
        records = []
        try:
            processor, model = self._load_vlm(vlm_model_id)
            for path in pending:
                try:
                    with Image.open(path) as original:
                        original = ImageOps.exif_transpose(original).convert('RGB')
                    # Caption always comes from original pixels, before enhancement.
                    caption = self._caption(original, processor, model, trigger_word, max_new_tokens,
                                            training_focus, custom_focus)
                    final_image = self._resize(original, min_short_side, max_long_side, upscale_mode, upscale_model)
                    img_path, txt_path = dest / f'{path.stem}.png', dest / f'{path.stem}.txt'
                    # Save image first and caption last, so skip_existing only accepts finished pairs.
                    temp_img = dest / f'{path.stem}.partial.png'
                    final_image.save(temp_img, format='PNG')
                    temp_img.replace(img_path)
                    txt_path.write_text(caption + '\n', encoding='utf-8')
                    records.append({'file': path.name, 'status': 'ok', 'source_size': f'{original.width}x{original.height}', 'output_size': f'{final_image.width}x{final_image.height}', 'caption': caption})
                    processed += 1
                    LOG.info('LoRADatasetPrep: saved %s', path.stem)
                except Exception as exc:
                    records.append({'file': path.name, 'status': f'error: {exc}', 'source_size': '', 'output_size': '', 'caption': ''})
                    LOG.exception('Failed to prepare %s', path)
            with (dest / 'prep_report.csv').open('w', newline='', encoding='utf-8-sig') as fp:
                writer = csv.DictWriter(fp, fieldnames=['file', 'status', 'source_size', 'output_size', 'caption'])
                writer.writeheader()
                writer.writerows(records)
            index = write_review_index(dest, files, records)
            failures = len(pending) - processed
            message = f'Output: {dest} | processed {processed}, skipped {skipped}, failed {failures}. Review: {index}'
            if failures:
                LOG.warning(message)
            return (message, processed, skipped)
        finally:
            del model, processor
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

NODE_CLASS_MAPPINGS = {'LoRADatasetPrep': LoRADatasetPrep}
NODE_DISPLAY_NAME_MAPPINGS = {'LoRADatasetPrep': 'LoRA Dataset Prep (Batch Upscale + Caption)'}
