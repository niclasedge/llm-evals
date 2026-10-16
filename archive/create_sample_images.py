#!/usr/bin/env python3
"""
Create sample test images for vision testing.
Since we can't create actual complex images, we'll create simple colored rectangles
with text labels that can be used for basic vision testing.
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def create_simple_image(path: Path, width: int = 400, height: int = 300, color: tuple = (255, 0, 0), text: str = ""):
    """Create a simple colored image with optional text."""
    if not PIL_AVAILABLE:
        print("PIL not available. Creating placeholder files instead.")
        # Create an empty file as placeholder
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(f"# Placeholder image for {text or 'test'}\n")
            f.write(f"# Color: {color}\n")
            f.write(f"# Size: {width}x{height}\n")
        return
    
    # Create image with solid color background
    image = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(image)
    
    # Add text if provided
    if text:
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            font = None
        
        # Calculate text position (centered)
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = len(text) * 6  # Approximate
            text_height = 11  # Approximate
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Use contrasting color for text
        text_color = (255, 255, 255) if sum(color) < 384 else (0, 0, 0)
        draw.text((x, y), text, fill=text_color, font=font)
    
    # Save image
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, 'JPEG', quality=95)
    print(f"Created: {path}")

def create_chart_image(path: Path, chart_type: str = "bar"):
    """Create a simple chart image."""
    if not PIL_AVAILABLE:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(f"# Placeholder chart image: {chart_type}\n")
        return
    
    width, height = 500, 400
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Draw simple bar chart
    if chart_type == "bar":
        # Draw bars
        bar_width = 60
        bars = [100, 150, 200, 120, 180]  # Bar heights
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
        
        for i, (bar_height, color) in enumerate(zip(bars, colors)):
            x1 = 50 + i * (bar_width + 20)
            y1 = height - 50
            x2 = x1 + bar_width
            y2 = y1 - bar_height
            draw.rectangle([x1, y2, x2, y1], fill=color, outline=(0, 0, 0))
            
            # Add value labels
            draw.text((x1 + 10, y2 - 20), str(bar_height), fill=(0, 0, 0))
    
    # Add title
    draw.text((width//2 - 50, 20), f"{chart_type.title()} Chart", fill=(0, 0, 0))
    
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, 'JPEG', quality=95)
    print(f"Created chart: {path}")

def main():
    """Create sample images for vision testing."""
    base_path = Path("test_images")
    
    print("Creating sample vision test images...")
    
    # Object Recognition Images
    create_simple_image(base_path / "object_recognition/car_red.jpg", 
                       color=(255, 0, 0), text="RED CAR")
    create_simple_image(base_path / "object_recognition/cat_sitting.jpg", 
                       color=(139, 69, 19), text="CAT SITTING")
    create_simple_image(base_path / "object_recognition/multiple_fruits.jpg", 
                       color=(255, 165, 0), text="FRUITS IN BOWL")
    create_simple_image(base_path / "object_recognition/desk_setup.jpg", 
                       color=(160, 160, 160), text="COMPUTER DESK")
    create_simple_image(base_path / "object_recognition/kitchen_tools.jpg", 
                       color=(192, 192, 192), text="KITCHEN TOOLS")
    
    # Scene Description Images
    create_simple_image(base_path / "scene_description/living_room.jpg", 
                       color=(245, 245, 220), text="LIVING ROOM")
    create_simple_image(base_path / "scene_description/kitchen_cooking.jpg", 
                       color=(255, 228, 196), text="COOKING KITCHEN")
    create_simple_image(base_path / "scene_description/park_playground.jpg", 
                       color=(144, 238, 144), text="PARK PLAYGROUND")
    create_simple_image(base_path / "scene_description/street_busy.jpg", 
                       color=(169, 169, 169), text="BUSY STREET")
    create_simple_image(base_path / "scene_description/beach_sunset.jpg", 
                       color=(255, 140, 0), text="BEACH SUNSET")
    
    # Text in Image
    create_simple_image(base_path / "text_in_image/sign_restaurant.jpg", 
                       color=(255, 255, 255), text="RESTAURANT SIGN")
    create_simple_image(base_path / "text_in_image/book_cover.jpg", 
                       color=(70, 130, 180), text="BOOK TITLE")
    create_simple_image(base_path / "text_in_image/menu_prices.jpg", 
                       color=(255, 255, 240), text="MENU $10.99")
    create_simple_image(base_path / "text_in_image/note_handwritten.jpg", 
                       color=(255, 255, 224), text="Handwritten Note")
    create_simple_image(base_path / "text_in_image/newspaper_headline.jpg", 
                       color=(255, 255, 255), text="NEWS HEADLINE")
    
    # Visual Reasoning
    create_simple_image(base_path / "visual_reasoning/sequence_shapes.jpg", 
                       color=(230, 230, 250), text="□ ○ △ □ ○ ?")
    create_simple_image(base_path / "visual_reasoning/pattern_colors.jpg", 
                       color=(255, 192, 203), text="R G B R G ?")
    create_simple_image(base_path / "visual_reasoning/jigsaw_piece.jpg", 
                       color=(176, 196, 222), text="JIGSAW PUZZLE")
    create_simple_image(base_path / "visual_reasoning/maze_solution.jpg", 
                       color=(240, 248, 255), text="MAZE PATH")
    create_simple_image(base_path / "visual_reasoning/optical_illusion.jpg", 
                       color=(255, 250, 205), text="OPTICAL ILLUSION")
    
    # Chart Analysis
    create_chart_image(base_path / "chart_analysis/sales_quarterly.jpg", "bar")
    create_chart_image(base_path / "chart_analysis/population_cities.jpg", "bar")
    create_chart_image(base_path / "chart_analysis/temperature_months.jpg", "line")
    create_chart_image(base_path / "chart_analysis/stock_price.jpg", "line")
    create_chart_image(base_path / "chart_analysis/market_share.jpg", "pie")
    
    print(f"\nSample images created in {base_path}")
    print("Note: These are simple test images for demonstration purposes.")
    print("For production use, replace with actual photographs and charts.")

if __name__ == "__main__":
    main()