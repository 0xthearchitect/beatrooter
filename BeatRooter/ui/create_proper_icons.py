from PIL import Image, ImageDraw, ImageFont

def create_icon(text, bg_color, output_path):
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = size // 10
        draw.rounded_rectangle(
            (margin, margin, size - margin, size - margin),
            radius=size // 6,
            fill=bg_color
        )

        try:
            font = ImageFont.truetype("arial.ttf", size // 3)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        draw.text(
            ((size - w) // 2, (size - h) // 2),
            text,
            font=font,
            fill=(255, 255, 255, 255)
        )

        images.append(img)

    # Gerar .ico com TODOS os tamanhos
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes]
    )

    print(f"Ícone criado corretamente → {output_path}")


# Criar ícones
create_icon("BRS", (33, 150, 243), "brs_file.ico")
create_icon("BRT", (244, 67, 54), "brt_file.ico")
create_icon("BR",   (76, 175, 80), "app_icon.ico")
