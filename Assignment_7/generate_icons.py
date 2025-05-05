from PIL import Image, ImageDraw

def create_icon(size, color, output_path):
    # Create a new image with white background
    image = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # Calculate dimensions
    outer_radius = int(size * 0.47)
    middle_radius = int(size * 0.35)
    inner_radius = int(size * 0.23)
    center = size // 2
    
    # Draw circles
    draw.ellipse(
        [center - outer_radius, center - outer_radius,
         center + outer_radius, center + outer_radius],
        fill=color
    )
    draw.ellipse(
        [center - middle_radius, center - middle_radius,
         center + middle_radius, center + middle_radius],
        fill='white'
    )
    draw.ellipse(
        [center - inner_radius, center - inner_radius,
         center + inner_radius, center + inner_radius],
        fill=color
    )
    
    # Save the image
    image.save(output_path, 'PNG')

# Generate active icons
for size in [16, 48, 128]:
    create_icon(size, '#4285f4', f'extension/icons/icon{size}.png')
    create_icon(size, '#cccccc', f'extension/icons/icon{size}_disabled.png') 