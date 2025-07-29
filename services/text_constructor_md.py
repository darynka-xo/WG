from operator import itemgetter

def json_to_markdown(json_output, space_threshold=10, y_tolerance=5):
    md_pages = []

    for page_num, page in enumerate(json_output['pages']):
        page_width, page_height = page['dimensions']
        word_items = []

        for block in page['blocks']:
            for line in block['lines']:
                for word in line['words']:
                    x0, y0 = word['geometry'][0]
                    x1, y1 = word['geometry'][1]

                    # Convert normalized coordinates to absolute pixel positions
                    abs_x = int(x0 * page_width)
                    abs_y = int(y0 * page_height)

                    word_items.append({
                        "text": word['value'],
                        "x": abs_x,
                        "y": abs_y,
                    })

        # Sort top-to-bottom, then left-to-right
        word_items.sort(key=lambda w: (w['y'], w['x']))

        # Group into lines
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

        # Generate Markdown lines
        markdown_lines = [f"<!-- Page {page_num + 1} -->\n"]

        for line in lines:
            line.sort(key=itemgetter("x"))
            words = [w['text'] for w in line]
            joined = " ".join(words)

            # Heuristic: lines in ALL CAPS are headers
            if joined.isupper() and len(joined) > 10:
                markdown_lines.append(f"### {joined}")
            elif len(words) > 4 and all(len(w) < 12 for w in words):
                # Looks like a paragraph
                markdown_lines.append(joined)
            else:
                markdown_lines.append(joined)

        md_pages.append("\n\n".join(markdown_lines))

    return "\n\n---\n\n".join(md_pages)  # Add horizontal rules between pages
