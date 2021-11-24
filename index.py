import math
import json

import io
import os
from PIL import Image
import requests

from fpdf import FPDF

def add_page(pdf, columns, rows):
    pdf.add_page(orientation = 'P')
    for i in range(rows):
        offset = pdf.h / rows
        pdf.line(0, offset*i, pdf.w, offset*i)
    for i in range(columns):
        offset = pdf.w / columns
        pdf.line(offset*i, 0, offset*i, pdf.h)

def spread(ret):
    spreaded = []
    for v in ret:
        if isinstance(v, list):
            spreaded = [*spreaded, *v]
        else:
            spreaded.append(v)
    return spreaded

def write_legend(pdf, pictures, columns, rows):
    add_page(pdf, columns, rows)
    x_diff = pdf.w - (pdf.w / columns)
    for pic in pictures:
        pdf.set_xy(x_diff - pic['x'], pic['y'])
        pdf.multi_cell(w=pic['w'], h=8, txt=pic['text'].encode('latin-1', "ignore").decode("latin-1"))

def should_keep_the_block(block):
    if block['type'] == 'toggle':
    #    return block['toggle']['text'][0]['annotations']['color'] != 'default'
        return True

    return block['type'] == 'image'
    
def walk(block, parent_text = ''):
    if 'object' in block and block['object'] == 'list':
        ret = list(map(
            lambda c: walk(c, parent_text), list(filter(
                should_keep_the_block, block['results']
            ))))
        return ret

    elif block['type'] == 'toggle':
        id = block['id']
        text = block['toggle']['text'][0]['text']['content']
        url = f'https://{NOTION_API_ENDPOINT}/v1/blocks/{id}/children'
        r = requests.get(url=url, headers=headers)
        children = r.json()
        text_new = parent_text + ' - ' + text if parent_text != '' else text
        ret =  walk(children, text_new)
        return spread(ret)

    elif block['type'] == 'image':
        url = block['image']['file']['url']
        return {
            'text': parent_text,
            'url': url
        }

NOTION_KEY=os.environ['NOTION_KEY']
NOTION_API_ENDPOINT="api.notion.com"

#NOTION_PAGE_ID="4b6b2a84dadd45b784f921e8264bc08d"
# NOTION_PAGE_ID="3f464f5515b247e59553a4e454493be4"

# page test
NOTION_PAGE_ID="58de70dd2b8d45ff976daf88e0b8e27a"

SIZE_FACTOR=5

headers = {
    'Authorization': f'Bearer {NOTION_KEY}',
    'Notion-Version': '2021-08-16'
}

url = f'https://{NOTION_API_ENDPOINT}/v1/blocks/{NOTION_PAGE_ID}/children'
r = requests.get(url=url, headers=headers)
data = r.json()

pictures = []
print(f"Going to fetch {len(data['results'])}")
pictures = spread(walk(data))
print(json.dumps(pictures, indent=4, sort_keys=True))

pdf = FPDF(format='A4', orientation = 'P')
pdf.set_font('Helvetica', '', 10)

total = len(pictures)
rows = 4
columns = 4
pages = math.ceil(total / (rows*columns))

pictures_page = []
for i, img in enumerate(pictures):
    if i % (rows * columns) == 0:
        if i != 0:
            write_legend(pdf, pictures_page, columns, rows)
            pictures_page = []
        add_page(pdf, columns, rows)

    if not 'url' in img:
        print('skipping')
        continue
    img_data = Image.open(io.BytesIO(requests.get(img['url']).content))
    width, height = img_data.size

    if height / width < 1:
        img_data = img_data.transpose(Image.ROTATE_90)
        width, height = img_data.size

    ratio = height / width

    w = pdf.w / columns
    h = pdf.h / rows

    if h / w < ratio:
        hh = h
        ww = hh / ratio
    else:
        ww = w
        hh = w * ratio

    new_size = (int(ww*SIZE_FACTOR), int(hh*SIZE_FACTOR))
    img_data = img_data.resize(size=new_size)

    x = (i % columns) * w
    y = math.floor((i % (rows * columns)) / rows) * h

    pictures_page.append({
        'text': img['text'],
        'x': x,
        'y': y,
        'w': ww,
        'h': hh
    })

    # Centering
    x = x + (w - ww) / 2
    y = y + (h - hh) / 2

    pdf.image(img_data, x=x, y=y, w=ww, h=hh)
write_legend(pdf, pictures_page, columns, rows)

pdf.output('moderne.pdf','F')
