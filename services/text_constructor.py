from operator import itemgetter

def reconstruct_text(json_output, space_threshold=10, y_tolerance=5):
    text_pages = []

    for page in json_output['pages']:
        page_width, page_height = page['dimensions']
        word_items = []

        for block in page['blocks']:
            for line in block['lines']:
                for word in line['words']:
                    x0, y0 = word['geometry'][0]
                    x1, y1 = word['geometry'][1]

                    # Convert normalized coordinates to absolute pixel values
                    abs_x = int(x0 * page_width)
                    abs_y = int(y0 * page_height)

                    word_items.append({
                        "text": word['value'],
                        "x": abs_x,
                        "y": abs_y,
                    })

        # Sort words by y (top to bottom), then x (left to right)
        word_items.sort(key=lambda w: (w['y'], w['x']))

        # Group into lines based on y proximity
        lines = []
        current_line = []
        prev_y = None

        for word in word_items:
            if prev_y is None or abs(word['y'] - prev_y) <= y_tolerance:
                current_line.append(word)
            else:
                lines.append(current_line)
                current_line = [word]
            prev_y = word['y']

        if current_line:
            lines.append(current_line)

        # Build text lines with spacing
        text_lines = []
        for line in lines:
            line.sort(key=itemgetter("x"))
            line_text = ""

            prev_x = None
            for word in line:
                if prev_x is not None:
                    gap = word['x'] - prev_x
                    if gap > space_threshold:
                        line_text += " "
                line_text += word['text']
                prev_x = word['x'] + len(word['text']) * 6  # Approximate word width

            text_lines.append(line_text)

        # Combine lines
        text_pages.append("\n".join(text_lines))

    return "\n\n".join(text_pages)
