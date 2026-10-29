"""Training-caption instructions for different LoRA targets."""

FOCUS_HINTS = {
    'auto': 'Describe the main visible subject and its most distinctive visual attributes. Include relevant setting and composition.',
    'person': 'Focus on the visible person: hairstyle, clothing, pose, expression, framing, and setting. Do not infer identity, ethnicity, or exact age.',
    'object': 'Focus on the object: shape, materials, colors, surface details, orientation, and how it is shown.',
    'background': 'Focus on the environment: layout, architecture or landscape, depth, colors, lighting, and atmosphere.',
    'outfit': 'Focus on the clothing or costume: garment types, silhouette, materials, colors, patterns, accessories, and how they are worn.',
    'item': 'Focus on the featured item or prop: shape, materials, colors, distinctive details, and its placement or use.',
    'pose': 'Focus on the visible body pose: limb positions, posture, orientation, gesture, and framing.',
    'art_style': 'Focus on the visible visual style: medium, linework, brushwork or rendering, palette, texture, shading, and recurring design features. Do not guess an artist.',
    'visual_effect': 'Focus on the visible effect: its appearance, color, texture, intensity, position, and interaction with the scene.',
    'expression': 'Focus on the visible facial expression: eyes, mouth, brows, head position, and any supporting gesture. Do not infer personality or inner thoughts.',
    'camera_angle': 'Focus on the viewpoint: camera height, direction, tilt, perspective, subject orientation, and framing.',
    'composition': 'Focus on the arrangement: subject placement, crop, scale, balance, negative space, depth, and leading lines.',
    'logo': 'Focus on the visible logo: shapes, typography, colors, layout, and background. Transcribe text only when clearly legible; do not invent a brand name.',
    'symbol': 'Focus on the visible symbol or icon: geometry, colors, line weight, internal details, symmetry, and placement. Do not infer a meaning without visual evidence.',
    'custom': '',
}


def build_caption_instruction(training_focus: str, custom_focus: str = '') -> str:
    """Build a grounded instruction without assuming the image is a photograph."""
    if training_focus not in FOCUS_HINTS:
        raise ValueError(f'Unknown training_focus: {training_focus}')
    custom_focus = custom_focus.strip()
    if training_focus == 'custom' and not custom_focus:
        raise ValueError('custom_focus is required when training_focus=custom')

    parts = [
        'Write ONLY one concise English caption for training an image-generation LoRA.',
        'Describe what is actually visible, whether the image is a photo, illustration, graphic, or render.',
    ]
    if FOCUS_HINTS[training_focus]:
        parts.append(FOCUS_HINTS[training_focus])
    if custom_focus:
        parts.append(f'Additional focus: {custom_focus}')
    parts.extend([
        'Mention only relevant surrounding details; keep the target aspect prominent.',
        'Do not invent hidden details, proper names, or text that cannot be read clearly.',
        'Do not include a preamble, bullet points, or image-quality tags.',
    ])
    return ' '.join(parts)


def format_caption(trigger_word: str, generated_text: str) -> str:
    """Prefix the generated caption while preserving case-sensitive visible text."""
    caption = ' '.join(generated_text.strip().split()).strip(' ,.\n')
    if not caption:
        raise ValueError('The VLM returned an empty caption.')
    trigger = trigger_word.strip()
    return f'{trigger}, {caption}' if trigger else caption
