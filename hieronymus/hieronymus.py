#! /usr/bin/env python

# TODO:
# * config yaml
# * move utils to separate module
# * color list mapping name: rgb
# * output to ELK/influx
# * close-up render top, body, base
# * configurable resolutions (or based on staff length?)
# * redis cache
# * remove defaults to allow individual parts
# * or better support for individual parts 


from __future__ import division
import os, sys, re
import itertools
import subprocess
import base64
import tempfile
import logging
 
from solid import *
from solid.utils import *
from solid import screw_thread
from flask import Flask, request, render_template
from flask_env import MetaFlaskEnv
from flask_cors import cross_origin

class GeneralConfiguration(metaclass=MetaFlaskEnv):
    '''
    These values may be overridden by environment variables.
    '''
    MODEL_DIR = '/data/models'
    MODEL_TOP_SUBDIR = 'top'
    MODEL_BODY_SUBDIR = 'body'
    MODEL_BASE_SUBDIR = 'base'
    MODEL_SUFFIX = 'stl'

    BODY_SECTIONS_DEFAULT = 1 

    OFFSET_BODY_FROM_TOP = 92
    OFFSET_BODY_FROM_BODY = 150
    OFFSET_BASE_FROM_TOP = 22

    RENDER_IMAGE_SIZE = '540,540'
    RENDER_CAMERA_COORDS = {
        0: '0,0,30,90,-30,0,600',
        1: '0,0,-50,90,-30,0,1000',
        2: '0,0,-140,90,-30,0,1300',
        3: '0,0,-210,90,-30,0,1700',
        4: '0,0,-280,90,-30,0,1900',
        5: '0,0,-350,90,-30,0,2200',
        6: '0,0,-430,90,-30,0,2600',
        7: '0,0,-510,90,-30,0,2900',
        8: '0,0,-590,90,-30,0,3300',
    }
    RENDER_COLOR_SCHEME = 'White'
    OPENSCAD_PATH= '/usr/bin/openscad'


class ModelConfiguration(GeneralConfiguration):
    '''
    These values will be loaded from file.
    '''
    COLORS = [
       "white",
       "black",
       "silver",
       "grey",
       "blue",
       "green",
       "red",
       "yellow",
       "orange",
       "purple",
    ]
    COLORS_TOP_DEFAULT = [
        'red',
    ]
    COLORS_BODY_DEFAULT = [
        'purple',
        'red',
    ]

    TOPS = {
        'dm-staff-of-natural-20': {
            'name': 'DM Staff of Natural 20',
        },
        'celtic-staff-of-life': {
            'name': 'Celtic Staff of Life',
        },
        'celtic-staff-of-luck': {
            'name': 'Celtic Staff of Luck',
        },
        'celtic-staff-of-family': {
            'name': 'Celtic Staff of Family',
        },
        'celtic-staff-of-strength': {
            'name': 'Celtic Staff of Strength',
        },
        'celtic-staff-of-triquetra': {
            'name': 'Celtic Staff of Triquetra',
        },
        'celtic-staff-of-bound-triquetra': {
            'name': 'Celtic Staff of Bound Triquetra',
        },
        'norse-staff-of-folk': {
            'name': 'Norse Staff of Folk',
        },
        'suite-staff-of-clubs': {
            'name': 'Suite Staff of Clubs',
        },
        'suite-staff-of-diamonds': {
            'name': 'Suite Staff of Diamonds',
        },
        'suite-staff-of-hearts': {
            'name': 'Suite Staff of Hearts',
        },
        'suite-staff-of-spades': {
            'name': 'Suite Staff of Spades',
        },
        'all-seeing-staff-of-horus': {
            'name': 'All-Seeing Staff of Horus',
        },
        'pagan-staff-of-pentacles': {
            'name': 'Pagan Staff of Pentacles',
        },
        'pumpkin-staff-of-tricks-and-treats': {
            'name': 'Pumpkin Staff of Tricks and Treats',
        },
        'soccer-staff-of-supporting': {
            'name': 'Soccer Staff of Supporting',
        },
        'harmonic-staff-of-balance': {
            'name': 'Harmonic Staff of Balance',
        },
        'emotive-staff-of-communication': {
            'name': 'Emotive Staff of Communication',
        },
        'hyrule-staff-of-power': {
            'name': 'Hyrule Staff of Power',
        },
        'evil-staff-of-empire': {
            'name': 'Evil Staff of Empire',
        },
        'noble-staff-of-rebellion': {
            'name': 'Noble Staff of Rebellion',
        },
        'frozen-staff-of-winter': {
            'name': 'Frozen Staff of Winter',
        },
        'vampiric-staff-of-alucard': {
            'name': 'Vampiric Staff of alucarD',
        },
        'twinkling-staff-of-starbursts': {
            'name': 'Twinkling Staff of Starbursts',
        },
        'yggdrasil-staff-of-world-tree': {
            'name': 'Yggdrasil Staff of World Tree',
        },
        'ruby-staff-of-development': {
            'name': 'Ruby Staff of Development',
        },
        'mercenary-staff-of-mouthiness': {
            'name': 'Mercenary Staff of Mouthiness',
        },
        'hieroglyph-staff-of-life': {
            'name': 'Hieroglyph Staff of Life',
        },
        'bat-staff-of-dark-knight': {
            'name': 'Bat Staff of Dark kNight',
        },
        'castle-staff-of-punishment': {
            'name': 'Castle Staff of Punishment',
        },
        'paranormal-staff-of-research': {
            'name': 'Paranormal Staff of Research',
        },
        'green-staff-of-will': {
            'name': 'Green Staff of Will',
        },
        'twinkling-staff-of-growth': {
            'name': 'Twinkling Staff of Growth',
        },
        'harlequin-staff-of-therapy': {
            'name': 'Harlequin Staff of Therapy',
        },
    }

    TOP_DEFAULT = 'none'

    BODIES = [
        'gnarled',
        'knurled',
        'sliced',
        'ruby',
    ]
    BODY_DEFAULT = 'none'

    BASES = [
        'endcap-round',
        'endcap-flat',
        'endcap-ruby',
        'display-round',
        'display-snowflake',
        'display-star',
    ]
    BASE_DEFAULT = 'none'


def load_top_model_paths():
    '''
    Determine model paths for defined tops if not specified in config.

    TODO: move this (and others) to separate module
    '''
    for top, params in app.config['TOPS'].items():
        if 'models' in params:
            continue
        top_path = os.path.join(app.config['MODEL_DIR'],
                                app.config['MODEL_TOP_SUBDIR'], top)
        app.config['TOPS'][top]['models'] = [
            os.path.join(top_path, f) for f in os.listdir(top_path)
            if f.split('.')[-1] == app.config['MODEL_SUFFIX']]
        app.logger.info('Loaded models for {0}: {1}'.format(top,
            app.config['TOPS'][top]['models']))


def get_top_scad(colors, model_paths):
    components = []
    colors = itertools.cycle(colors)
    for each in model_paths:
        model = import_stl(each)
        components.append(color(next(colors))(model))
    return union()(*components)


def get_body_scad(offset_top, offset_body, colors, model_path,
                  body_section_count):
    sections = []
    offset = offset_top
    colors = itertools.cycle(colors)
    model = import_stl(model_path)
    for _ in range(body_section_count):
        sections.append(up(offset)(color(next(colors))(model)))
        offset += offset_body
    return union()(*sections) 


def get_base_scad(offset_top, offset_body, colors, model_path,
                  body_section_count):
    offset = offset_top
    colors = itertools.cycle(colors)
    model = import_stl(model_path)
    for _ in range(body_section_count + 1):
        colour = next(colors)
    for _ in range(body_section_count):
        offset += offset_body
    return up(offset)(color(colour)(model))


def get_staff_scad(top_id, body_id, base_id, body_sections,
                   colors_top, colors_body):
    # HACK: to handle empty top and thus render topless
    try:
        top = get_top_scad(colors_top, app.config['TOPS'][top_id]['models'])
    except KeyError:
        top = get_top_scad(colors_top, [])
    body = get_body_scad(app.config['OFFSET_BODY_FROM_TOP'],
                         app.config['OFFSET_BODY_FROM_BODY'],
                         colors_body,
                         os.path.join(app.config['MODEL_DIR'], 
                                      app.config['MODEL_BODY_SUBDIR'],
                                      body_id + '.' + app.config['MODEL_SUFFIX']),
                         body_sections)
    base = get_base_scad(app.config['OFFSET_BASE_FROM_TOP'],
                         app.config['OFFSET_BODY_FROM_BODY'],
                         colors_body,
                         os.path.join(app.config['MODEL_DIR'],
                                      app.config['MODEL_BASE_SUBDIR'],
                                      base_id + '.' + app.config['MODEL_SUFFIX']),
                         body_sections)
    staff = rotate([180,0,0])(union()(top, body, base))
    return staff


def get_file_as_base64(path: str) -> str:
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string.decode()


def get_staff_img(model_top, model_body, model_base, body_sections,
                  colors_top, colors_body):
    staff_scad = get_staff_scad(model_top, model_body, model_base,
                                body_sections, colors_top, colors_body)
    with tempfile.NamedTemporaryFile() as scad_file, \
         tempfile.NamedTemporaryFile(suffix='.png') as image_file:
        scad_render_to_file(staff_scad, scad_file.name)
        try:
            s = subprocess.check_output(
                [
                    app.config['OPENSCAD_PATH'],
                    scad_file.name,
                    '-o', image_file.name,
                    '--camera=' + app.config['RENDER_CAMERA_COORDS'][body_sections],
                    '--imgsize=' + app.config['RENDER_IMAGE_SIZE'],
                    '--colorscheme=' + app.config['RENDER_COLOR_SCHEME'],
                ],
                stderr=subprocess.STDOUT,
                universal_newlines=True)
        except subprocess.CalledProcessError as err:
            app.logger.error(err.output)
        return get_file_as_base64(image_file.name)


app = Flask(__name__)
app.config.from_object(ModelConfiguration)
if not app.debug:
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.INFO)
load_top_model_paths()


@app.route("/", methods=['GET'])
def staff_designer():
    return render_template('staff_designer.html', colors=app.config['COLORS'],
                           models_top = app.config['TOPS'],
                           models_body = app.config['BODIES'],
                           models_base = app.config['BASES'])


@app.route("/render_staff", methods=['GET'])
#@cross_origin(origins="*.enstaved.com")
@cross_origin(origins="*")
def render_staff():
    embed = request.args.get('embed', False) == 'true'
    top_id = request.args.get('top-id',
                              app.config['TOP_DEFAULT'])
    body_id = request.args.get('body-id', app.config['BODY_DEFAULT'])
    base_id = request.args.get('base-id', app.config['BASE_DEFAULT'])
    body_sections = int(request.args.get('body-sections', app.config['BODY_SECTIONS_DEFAULT']))
    colors_top = request.args.getlist('top-color')
    if colors_top == []:
        colors_top = app.config['COLORS_TOP_DEFAULT']
    colors_body = request.args.getlist('body-color')
    if colors_body == []:
        colors_body = app.config['COLORS_BODY_DEFAULT']
    # TODO: validate these before continuing
    # wtforms/webargs/voluptuous
    image_base64 = get_staff_img(top_id, body_id, base_id, body_sections,
           colors_top, colors_body)
    if embed:
        return render_template('image_base64.html', image=image_base64, alt='staff')
    return 'data:image/png;base64, ' + image_base64




def main():
    app.run()
    return(os.EX_OK)


if __name__ == '__main__':
    sys.exit(main())
