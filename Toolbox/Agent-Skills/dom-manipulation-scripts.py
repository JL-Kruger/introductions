import re

def move_thumbnail_left(html_path):
    """
    Finds the .thumbnail-wrap and moves it to the bottom of the left bento column.
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    thumb_pattern = r'([ \t]*<div class="thumbnail-wrap".*?border-radius: 50%;" />\n[ \t]*</div>\n)'
    thumb_match = re.search(thumb_pattern, html, flags=re.DOTALL)

    if thumb_match:
        thumb_block = thumb_match.group(1)
        
        # Remove from its current place
        html = html.replace(thumb_block, '')
        
        # Insert it at the bottom of bento-left (assumes standard text structure)
        target = '<p>online and in the world around me.</p>\n                </div>'
        replacement = '<p>online and in the world around me.</p>\n' + thumb_block + '                </div>'
        html = html.replace(target, replacement)

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print("Success: Moved Thumbnail")
    else:
        print("Thumbnail not found or already moved.")


def move_critter_right(html_path):
    """
    Finds the .decor-critter, resizes it, and moves it to the bottom of the right bento column.
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    critter_pattern = r'([ \t]*<div class="decor-critter".*?</svg>\n[ \t]*</div>\n)'
    critter_match = re.search(critter_pattern, html, flags=re.DOTALL)

    if critter_match:
        critter_block = critter_match.group(1)
        
        # Remove from center
        html = html.replace(critter_block, '')
        
        # Update critter block height to strictly match 160px
        critter_block = critter_block.replace('max-width: 100px; max-height: 10vh;', 'width: 160px; height: 160px;')
        critter_block = critter_block.replace('max-width: 200px; max-height: 20vh;', 'width: 160px; height: 160px;')
        
        # Insert critter into right (at the end)
        target_end = '<p>Or flick around and find out. Your choice.</p>\n                </div>'
        replacement = '<p>Or flick around and find out. Your choice.</p>\n' + critter_block + '                </div>'
        html = html.replace(target_end, replacement)

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print("Success: Moved Critter")
    else:
        print("Critter not found or already moved.")


if __name__ == "__main__":
    move_critter_right('index.html')
    move_thumbnail_left('index.html')
