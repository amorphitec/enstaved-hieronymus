#! /usr/bin/env python

# TODO:
#
# * / demo page
# * containerise
# * toppers in dict w/list of models
#  * OR just trawl the dir on start
# * color list mapping name: rgb

from __future__ import division
import os, sys, re
import itertools
import subprocess
import base64
import tempfile
 
from solid import *
from solid.utils import *
from solid import screw_thread
from flask import Flask, request, render_template
from flask_env import MetaFlaskEnv


class GeneralConfiguration(metaclass=MetaFlaskEnv):
    '''
    These values may be overridden by environment variables.
    '''
    MODEL_DIR = '/home/james/Documents/Enstaved/STL_files/'
    MODEL_TOP_SUBDIR = 'top'
    MODEL_BODY_SUBDIR = 'body'
    MODEL_BASE_SUBDIR = 'base'
    MODEL_SUFFIX = '.stl'

    BODY_SECTIONS_DEFAULT = 8 

    OFFSET_BODY_FROM_TOP = 92
    OFFSET_BODY_FROM_BODY = 150
    OFFSET_BASE_FROM_TOP = 22

    RENDER_IMAGE_SIZE = '300,800'
    RENDER_CAMERA_COORDS = '0,0,-590,90,-15,0,3500'
    RENDER_COLOR_SCHEME = 'White'
    OPENSCAD_PATH= '/usr/bin/openscad'

class ModelConfiguration(GeneralConfiguration):
    '''
    TODO: These values will be loaded from file.
    '''
    COLORS = [
       "white",
       "black",
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

    MODELS_TOP = [
        'd20',
        'heart',
        'knot_simple_03',
        'pentagram_simple_01',
        'pumpkin',
    ]
    MODEL_TOP_DEFAULT = 'pumpkin'

    MODELS_BODY = [
        'gnarled',
        'knurled',
        'sliced',
    ]
    MODEL_BODY_DEFAULT = 'gnarled'

    MODELS_BASE = [
        'round',
        'flat',
    ]
    MODEL_BASE_DEFAULT = 'round'


app = Flask(__name__)
app.config.from_object(ModelConfiguration)
print(app.config)


def get_top_scad(colors, model_path):
    # TODO: cater for multi-part models
    colors = itertools.cycle(colors)
    model = import_stl(model_path)
    return color(next(colors))(model)


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


def get_staff_scad(model_top, model_body, model_base, body_sections,
                   colors_top, colors_body):
    top = get_top_scad(colors_top,
                       os.path.join(app.config['MODEL_DIR'],
                                    app.config['MODEL_TOP_SUBDIR'],
                                    model_top + app.config['MODEL_SUFFIX']))
    body = get_body_scad(app.config['OFFSET_BODY_FROM_TOP'],
                         app.config['OFFSET_BODY_FROM_BODY'],
                         colors_body,
                         os.path.join(app.config['MODEL_DIR'], 
                                      app.config['MODEL_BODY_SUBDIR'],
                                      model_body + app.config['MODEL_SUFFIX']),
                         body_sections)
    base = get_base_scad(app.config['OFFSET_BASE_FROM_TOP'],
                         app.config['OFFSET_BODY_FROM_BODY'],
                         colors_body,
                         os.path.join(app.config['MODEL_DIR'],
                                      app.config['MODEL_BASE_SUBDIR'],
                                      model_base + app.config['MODEL_SUFFIX']),
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
                    '--camera=' + app.config['RENDER_CAMERA_COORDS'],
                    '--imgsize=' + app.config['RENDER_IMAGE_SIZE'],
                    '--colorscheme=' + app.config['RENDER_COLOR_SCHEME'],
                ],
                stderr=subprocess.STDOUT,
                universal_newlines=True)
        except subprocess.CalledProcessError as err:
            # TODO: log this error
            print(err.output)
        return get_file_as_base64(image_file.name)


@app.route("/", methods=['GET'])
def staff_designer():
    return render_template('staff_designer.html', colors=app.config['COLORS'],
                           models_top = app.config['MODELS_TOP'],
                           models_body = app.config['MODELS_BODY'],
                           models_base = app.config['MODELS_BASE'])


@app.route("/render", methods=['GET'])
def render_staff():
    model_top = request.args.get('model-top',
                                 app.config['MODEL_TOP_DEFAULT'])
    model_body = request.args.get('model-body', app.config['MODEL_BODY_DEFAULT'])
    model_base = request.args.get('model-base', app.config['MODEL_BASE_DEFAULT'])
    body_sections = int(request.args.get('body-sections', app.config['BODY_SECTIONS_DEFAULT']))
    colors_top = request.args.getlist('color-top')
    if colors_top == []:
        colors_top = app.config['COLORS_TOP_DEFAULT']
    colors_body = request.args.getlist('color-body')
    if colors_body == []:
        colors_body = app.config['COLORS_BODY_DEFAULT']
    # TODO: validate these before continuing
    image_base64 = get_staff_img(model_top, model_body, model_base, body_sections,
           colors_top, colors_body)
    return render_template('image_base64.html', image=image_base64, alt='staff')
