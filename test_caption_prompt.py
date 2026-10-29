"""Tests for use-specific caption instructions and output formatting."""

import json
import unittest
from pathlib import Path

from caption_prompt import FOCUS_HINTS, build_caption_instruction, format_caption


class CaptionPromptTests(unittest.TestCase):
    def test_every_focus_builds_a_non_photo_specific_instruction(self):
        for focus in FOCUS_HINTS:
            with self.subTest(focus=focus):
                detail = 'emphasize embroidered motifs' if focus == 'custom' else ''
                instruction = build_caption_instruction(focus, detail)
                self.assertIn('LoRA', instruction)
                self.assertIn('photo, illustration, graphic, or render', instruction)
                self.assertNotIn('for this photograph', instruction)

    def test_focus_targets_are_distinct(self):
        self.assertIn('typography', build_caption_instruction('logo'))
        self.assertIn('linework', build_caption_instruction('art_style'))
        self.assertIn('limb positions', build_caption_instruction('pose'))
        self.assertIn('embroidery', build_caption_instruction('outfit', 'emphasize embroidery'))

    def test_custom_focus_requires_text(self):
        with self.assertRaises(ValueError):
            build_caption_instruction('custom', '  ')

    def test_preserves_case_and_allows_no_trigger(self):
        self.assertEqual(format_caption('MyLogo', 'ABC mark on blue.'), 'MyLogo, ABC mark on blue')
        self.assertEqual(format_caption(' ', '  Red   icon.  '), 'Red icon')

    def test_empty_caption_is_rejected(self):
        with self.assertRaises(ValueError):
            format_caption('token', ' ... ')

    def test_workflow_keeps_upscaler_link_and_focus_values(self):
        workflow = json.loads((Path(__file__).parent / 'workflows' / 'lora_dataset_preparation.json').read_text())
        node = next(node for node in workflow['nodes'] if node['type'] == 'LoRADatasetPrep')
        self.assertEqual(node['inputs'][10]['name'], 'upscale_model')
        self.assertEqual(node['inputs'][10]['link'], 1)
        self.assertEqual(workflow['links'][0][4], 10)
        self.assertEqual(node['widgets_values'][-2:], ['auto', ''])


if __name__ == '__main__':
    unittest.main()
