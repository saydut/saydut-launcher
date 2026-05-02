"""
QR Code Generation Logic
Core functions for QR generation and PDF export
"""
import re
from PIL import Image
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader


# ============================================================================
# TEXT PARSING
# ============================================================================

def split_pasted_text(text: str, split_commas: bool) -> list[str]:
    """
    Parse pasted text into list of items

    Args:
        text: Raw pasted text
        split_commas: Whether to split on commas/semicolons

    Returns:
        list[str]: Cleaned list of items

    Example:
        >>> split_pasted_text("item1, item2; item3", True)
        ['item1', 'item2', 'item3']
    """
    raw = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []

    for ln in raw.split("\n"):
        ln = ln.strip()
        if not ln:
            continue

        if split_commas:
            parts = re.split(r"[;,]+", ln)
            parts = [p.strip() for p in parts if p.strip()]
            lines.extend(parts)
        else:
            lines.append(ln)

    return lines


def build_plaintext_payload(
    location: str,
    items: list[str],
    numbering: bool,
    include_location: bool
) -> str:
    """
    Build the plaintext payload for QR code

    Args:
        location: Location/rack name
        items: List of part names
        numbering: Add numbering to items
        include_location: Include location in payload

    Returns:
        str: Plaintext payload

    Raises:
        ValueError: If items list is empty

    Example:
        >>> build_plaintext_payload("PALET 2", ["Motor", "Vites"], True, True)
        'PALET 2\n1. Motor\n2. Vites'
    """
    if not items:
        raise ValueError("Parça listesi boş olamaz.")

    location = (location or "").strip()

    # Add numbering if requested
    if numbering:
        body_lines = [f"{i+1}. {x}" for i, x in enumerate(items)]
    else:
        body_lines = items

    # Add location header
    header = ""
    if include_location and location:
        header = f"{location}\n"

    return header + "\n".join(body_lines)


# ============================================================================
# QR CODE GENERATION
# ============================================================================

def make_qr_image(
    data: str,
    box_size: int,
    border: int,
    err_level: str
) -> Image.Image:
    """
    Generate QR code image

    Args:
        data: Data to encode
        box_size: Size of each QR box (pixels)
        border: Border size (boxes)
        err_level: Error correction level

    Returns:
        PIL.Image: QR code image (RGB)

    Example:
        >>> img = make_qr_image("Hello", 10, 4, "Q (yüksek)")
    """
    err_map = {
        "L (düşük)": qrcode.constants.ERROR_CORRECT_L,
        "M (orta)": qrcode.constants.ERROR_CORRECT_M,
        "Q (yüksek)": qrcode.constants.ERROR_CORRECT_Q,
        "H (çok yüksek)": qrcode.constants.ERROR_CORRECT_H,
    }

    qr = qrcode.QRCode(
        version=None,
        error_correction=err_map.get(err_level, qrcode.constants.ERROR_CORRECT_Q),
        box_size=max(2, int(box_size)),
        border=max(4, int(border)),
    )

    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return img.convert("RGB")


# ============================================================================
# PDF EXPORT
# ============================================================================

def pdf_grid_config(layout: str) -> tuple[int, int]:
    """
    Get PDF grid configuration (rows, cols)

    Args:
        layout: Layout name

    Returns:
        tuple[int, int]: (rows, cols)

    Example:
        >>> pdf_grid_config("4 (2x2)")
        (2, 2)
    """
    if layout == "4 (2x2)":
        return 2, 2
    if layout == "6 (3x2)":
        return 3, 2
    if layout == "8 (4x2)":
        return 4, 2
    return 2, 2


def create_labels_pdf(
    pdf_path: str,
    qr_img: Image.Image,
    payload: str,
    layout: str,
    show_text: bool,
    title_text: str
) -> None:
    """
    Create PDF with QR code labels

    Args:
        pdf_path: Output PDF path
        qr_img: QR code image
        payload: Plaintext payload (for text display)
        layout: Grid layout (e.g., "4 (2x2)")
        show_text: Whether to show text under QR
        title_text: Title text to display

    Example:
        >>> create_labels_pdf(
        ...     "labels.pdf",
        ...     qr_img,
        ...     "PALET 2\nMotor\nVites",
        ...     "4 (2x2)",
        ...     True,
        ...     "Depo Malzemeleri"
        ... )
    """
    c = canvas.Canvas(pdf_path, pagesize=A4)
    page_w, page_h = A4

    rows, cols = pdf_grid_config(layout)
    margin = 28
    gap = 14

    usable_w = page_w - 2 * margin - (cols - 1) * gap
    usable_h = page_h - 2 * margin - (rows - 1) * gap

    cell_w = usable_w / cols
    cell_h = usable_h / rows

    text_h = 34 if show_text else 0
    qr_size = min(cell_w, cell_h - text_h)

    # Resize QR for PDF
    qr_for_pdf = qr_img.copy().resize((1000, 1000), Image.NEAREST)
    qr_reader = ImageReader(qr_for_pdf)

    # Prepare short text (first 4 lines + ...)
    lines = [ln.strip() for ln in payload.splitlines() if ln.strip()]
    short_lines = lines[:4]
    short_text = "\n".join(short_lines)
    if len(lines) > 4:
        short_text += "\n..."

    # Draw labels grid
    for r in range(rows):
        for col in range(cols):
            x = margin + col * (cell_w + gap)
            y = page_h - margin - (r + 1) * cell_h - r * gap

            qr_x = x + (cell_w - qr_size) / 2
            qr_y = y + (cell_h - text_h - qr_size) / 2 + (text_h if show_text else 0)

            # Draw QR code
            c.drawImage(
                qr_reader, qr_x, qr_y,
                width=qr_size, height=qr_size,
                preserveAspectRatio=True, mask='auto'
            )

            # Draw text (if enabled)
            if show_text:
                tx = x + 6
                ty = y + 6

                # Title
                if title_text.strip():
                    c.setFont("Helvetica-Bold", 8)
                    c.drawString(tx, ty + 22, title_text.strip()[:55])

                # Payload lines
                c.setFont("Helvetica", 7.5)
                yy = ty + 10
                for ln in short_text.splitlines():
                    c.drawString(tx, yy, ln[:70])
                    yy -= 9

            # Cell border
            c.setLineWidth(0.3)
            c.rect(x, y, cell_w, cell_h)

    c.showPage()
    c.save()


def save_payload_txt(base_path_no_ext: str, payload: str) -> str:
    """
    Save payload as .txt file

    Args:
        base_path_no_ext: Path without extension
        payload: Text payload

    Returns:
        str: Created .txt file path

    Example:
        >>> save_payload_txt("/path/to/qr", "Hello\\nWorld")
        '/path/to/qr.txt'
    """
    txt_path = base_path_no_ext + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(payload)
    return txt_path
