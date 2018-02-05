import argparse

from yaml import load

from px2pt import px2pt
from base_objects import Stroke


parser = argparse.ArgumentParser(prog='px2ph', description='Pixel to vector converter')
parser.add_argument('yamlpath', help='path to the yaml config file')
args = parser.parse_args()

config = None
with open(args.yamlpath, 'r') as yaml:
    config = load(yaml.read())

glyphs = px2pt(config['glyph_set'], **config['px_infos'])
glyphs = {glyph: Stroke(glyphs[glyph]) for glyph in glyphs}

glyphs['B'].layers = glyphs['B'].relative_points()
print(glyphs['B'].layers)
#
# print(glyphs)
