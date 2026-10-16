# Vision Test Images

This directory contains test images organized by category for vision model evaluation.

## Directory Structure

- `object_recognition/` - Simple object identification tests
- `scene_description/` - Complex scene analysis tests  
- `text_in_image/` - OCR and text extraction tests
- `visual_reasoning/` - Logic and reasoning tasks
- `chart_analysis/` - Data visualization interpretation tests

## Usage

These images are used by the vision evaluation framework to test the capabilities of vision-enabled LLM models. Each category tests different aspects of visual understanding:

### Object Recognition
- Single object identification
- Multiple object counting
- Object attribute description (color, size, shape)

### Scene Description
- Overall scene summarization
- Activity identification
- Spatial relationship understanding

### Text in Image
- OCR accuracy
- Handwriting recognition
- Sign and label reading

### Visual Reasoning
- Pattern recognition
- Logical deduction from visual cues
- Comparative analysis

### Chart Analysis
- Data extraction from graphs
- Trend identification
- Statistical interpretation

## Adding New Images

To add new test images:

1. Place images in the appropriate category directory
2. Update the corresponding vision test cases in `src/features/llm_evaluation/vision_test_cases.py`
3. Ensure images are in supported formats (PNG, JPG, JPEG, BMP, GIF)
4. Keep file sizes reasonable (< 10MB) for efficient processing

## Image Requirements

- Supported formats: PNG, JPG, JPEG, BMP, GIF
- Maximum size: 10MB per image
- Minimum resolution: 224x224 pixels
- Maximum resolution: 4096x4096 pixels