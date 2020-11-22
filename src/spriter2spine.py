## -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import xmltodict
import json
import math
import sys
import os
import re
import argparse

# spine file extension
SPINE_EXT = 'json'


def load_xml(path):
    tree = ET.parse(path)
    xml_data = tree.getroot()
    xmlstr = ET.tostring(xml_data, encoding='utf8', method='xml')
    data_dict = dict(xmltodict.parse(xmlstr))
    return data_dict


def write_json(data_dict, path): 
    with open(path, 'w+') as json_file:
        json.dump(data_dict, json_file, indent=4, sort_keys=True)


def load_tags(obj, name):
    if not obj.has_key(name):
        return [] 

    tag_objs = obj[name]
    if type(tag_objs).__name__ != 'list':
        return [tag_objs]

    return tag_objs


def load_float(obj, name, default=None):
    if not obj.has_key(name): return default
    return float(obj[name])


def gen_spine_obj(name):
    return {
            'skeleton': {
                'name': name,
                'width': 0,
                'height': 0,
                'hash': ' ',
                'spine': '3.8.99',
                'fps': 30
            },
            'bones': [],
            'slots': [],
            'animations': {},
            'skins': [
                {'name': 'default', 'attachments': {}},
            ]
     }


def get_attachment_name(pic_name):
    name = pic_name
    ext_index = name.lower().rfind('.png')
    if ext_index >= 0:
        name = name[0:ext_index] 
    return name


def calc_spine_time(spriter_time):
    return round(spriter_time / 1000.0, 3)


# to make a more cleaner data object,
# the spriter data format is too dirty!
def extract_spriter_data(in_path):
    xml_root = load_xml(in_path)['spriter_data']

    xml_folders = load_tags(xml_root, 'folder')
    folder_file_map = {}
    for _, folder in enumerate(xml_folders):
        k = folder['@id']
        folder_file_map[k] = {}
        files = load_tags(folder, 'file')
        for _, f in enumerate(files):
            folder_file_map[k][f['@id']] = {
               'name': f['@name'],
               'width': float(f['@width']),
               'height': float(f['@height']),
               'pivotx': float(f['@pivot_x']),
               'pivoty': float(f['@pivot_y'])
            }
    xml_entities = load_tags(xml_root, 'entity')
    entities = []
    for _, e in enumerate(xml_entities):
        eobj = {
                'name': e['@name'],
                'anis': [],
                'bones': []
        }
        entities.append(eobj)

        xml_obj_infos = load_tags(e, 'obj_info')
        for _, oi in enumerate(xml_obj_infos):
            if oi['@type'] != 'bone': continue
            eobj['bones'].append({'name': oi['@name'], 'length': float(oi['@w'])})

        xml_anis = load_tags(e, 'animation')
        for _, a in enumerate(xml_anis):
            ani = {
                'name': a['@name'],
                'interval': float(a['@interval']),
                'length': float(a['@length']),
                'looping': not a.has_key('@looping') and True or a['@looping'] == 'true',
                'l': float(a.has_key('@l') and a['@l'] or 0),
                'r': float(a.has_key('@r') and a['@r'] or 100),
                't': float(a.has_key('@t') and a['@t'] or 0),
                'b': float(a.has_key('@b') and a['@b'] or 100),
                'key': {},
                'timelines': {}
            }

            eobj['anis'].append(ani)

            xml_keys = load_tags(a['mainline'], 'key')
            for _, k in enumerate(xml_keys):
                aobj = {'bone_ref': {}, 'obj_ref': {}, 'time': k.has_key('@time') and float(k['@time']) or 0}
                ani['key'][k['@id']] = aobj
                for _, br in enumerate(load_tags(k, 'bone_ref')):
                    aobj['bone_ref'][br['@id']] = {
                        'timeline_id': br['@timeline'],
                        'parent': br.has_key('@parent') and br['@parent'] or None
                    }

                for _, br in enumerate(load_tags(k, 'object_ref')):
                    aobj['obj_ref'][br['@id']] = {
                        'timeline_id': br['@timeline'],
                        'z_index': int(br['@z_index']),
                        'parent': br.has_key('@parent') and br['@parent'] or None
                    }

            xml_timelines = load_tags(a, 'timeline')
            timelines = ani['timelines']
            for _, xml_timeline in enumerate(xml_timelines):
                timeline = {
                    'id': xml_timeline['@id'],
                    'name': xml_timeline['@name'],
                    'kfrms': [],
                    'is_bone': xml_timeline.has_key('@object_type'),
                }
                timelines[xml_timeline['@id']] = timeline
                kfrms = timeline['kfrms']
                xml_kfrms = load_tags(xml_timeline, 'key') 
                for _, xml_kfrm in enumerate(xml_kfrms):
                    kfrm = {}
                    kfrms.append(kfrm)

                    kfrm['time'] = xml_kfrm.has_key('@time') and float(xml_kfrm['@time']) or 0

                    objk = timeline['is_bone'] and 'bone' or 'object'

                    kfrm['x'] = load_float(xml_kfrm[objk], '@x')
                    kfrm['y'] = load_float(xml_kfrm[objk], '@y')
                    kfrm['scalex'] = load_float(xml_kfrm[objk], '@scale_x')
                    kfrm['scaley'] = load_float(xml_kfrm[objk], '@scale_y')
                    kfrm['angle'] = load_float(xml_kfrm[objk], '@angle')
                    kfrm['alpha'] = load_float(xml_kfrm[objk], '@a')
                    kfrm['folder'] = (not timeline['is_bone']) and xml_kfrm[objk]['@folder'] or None
                    kfrm['file'] = (not timeline['is_bone']) and xml_kfrm[objk]['@file'] or None
                    kfrm['curve'] = xml_kfrm.has_key('@curve_type') and xml_kfrm['@curve_type'] or None
                    kfrm['c1'] = load_float(xml_kfrm, '@c1')
                    kfrm['c2'] = load_float(xml_kfrm, '@c2')
                    kfrm['c3'] = load_float(xml_kfrm, '@c3')
                    kfrm['c4'] = load_float(xml_kfrm, '@c4')

    return (entities, folder_file_map)

def sort_parent(parent, root_first):
    depth = {}
    lst = []
    for k in parent.keys():
        lst.append(k)
        if depth.has_key(k): continue

        cur_k = k
        dep = 0

        while parent.has_key(cur_k):
            dep = dep + 1
            cur_k = parent[cur_k]
            if depth.has_key(cur_k):
                dep = depth[cur_k] + dep
                break

        depth[k] = dep

        cur_k = k
        while dep > 0:
            dep = dep - 1
            cur_k = parent[cur_k]
            if depth.has_key(cur_k): break
            depth[cur_k] = dep

    lst.sort(key=lambda a: depth[a], reverse=not root_first)
    return lst


def save_children(parent, bone_lst, bone_init_info):
    for _, name in enumerate(reversed(bone_lst)):
        if not parent.has_key(name):
            continue

        p = parent[name]

        if not bone_init_info.has_key(p):
            continue

        bone_init_info[p]['children'] = bone_init_info[p].has_key('children') and bone_init_info[p]['children'] or []
        bone_init_info[p]['children'].append(name)


def find_scales_in_keyfrm_state(time, states, default_sx, default_sy):
    cur_st = None
    for i, st in enumerate(reversed(states)):
        if time >= st['time']:
            cur_st = st
            break

    psx, psy = 1, 1
    if not cur_st:
        psx = default_sx
        psy = default_sy
    else:
        psx = cur_st['sx']
        psy = cur_st['sy']

    return (psx, psy)


def calcPosAndRotation(w, h, pivotx, pivoty, fx, fy, angle, scalex, scaley):
    x = (0.5 - pivotx) * w * scalex
    y = (0.5 - pivoty) * h * scaley

    if angle:
        radian = angle * math.pi / 180
        rx = x * math.cos(radian) - y * math.sin(radian)
        ry = x * math.sin(radian) + y * math.cos(radian)
        x, y = rx, ry

    x, y = x + fx, y + fy

    return (x, y, angle)


def extract_skeleton_data(skeleton_data, entity):
    # 1024 just mean a huge interval.
    min_interval, max_width, max_height = 1024, 0, 0
    for _, ani in enumerate(entity['anis']):
        min_interval = min(ani['interval'], ani['interval'])
        max_width = max(ani['r'] - ani['l'], max_width)
        max_height = max(ani['b'] - ani['t'], max_height)

    skeleton_data['fps'] = int(1000 / min_interval)
    skeleton_data['width'] = int(max_width)
    skeleton_data['height'] = int(max_height)


def extract_bone_data(bones, entity, folder_file_map, bone_init_info, ani_timeline_obj_key):
    bone_length = {}
    for _, b in enumerate(entity['bones']):
        bone_length[b['name']] = b['length']

    parent = {}
    for _, ani in enumerate(entity['anis']):
        # spine not natively supported bone hierarchy animation,
        # although we can use some constraints to simulate, it's too complecated!
        # so, here we check if have any hierarchy animation.
        result, reason = check_hierarchy_animation(ani['key'])
        if not result:
            print '[WARNING] Unsupported bone hierarchy animation: entity name(%s) ani name(%s) %s' % (entity['name'], ani['name'], reason)
            return False

        timeline_obj_key = {}
        ani_timeline_obj_key[ani['name']] = timeline_obj_key

        local_parent = {}
        timelines = ani['timelines']
        boneid2name = {}
        name2timeline = {}
        name2zindex = {}

        timelineid2bone = {}
        for key in ani['key'].values():
            for bone_id, v in key['bone_ref'].items():
                bone_name = timelines[v['timeline_id']]['name']
                boneid2name[bone_id] = bone_name
                timelineid2bone[v['timeline_id']] = v

            for obj_id, v in key['obj_ref'].items():
                timelineid2bone[v['timeline_id']] = v

        for timeline_id, v in timelineid2bone.items():
            parent_id = v['parent']
            bone_name = timelines[timeline_id]['name']
            if v.has_key('z_index'):
                bone_name = 'ext_%s' % bone_name
                name2zindex[bone_name] = v['z_index']

            local_parent[bone_name] = boneid2name.has_key(parent_id) and boneid2name[parent_id] or None
            name2timeline[bone_name] = timelines[timeline_id]

        merge_parent(parent, local_parent, bone_length, bone_init_info, timeline_obj_key, name2timeline, name2zindex)

    bones.append({'name': 'root'}) 
    bone_lst = sort_parent(parent, True)
    save_children(parent, bone_lst, bone_init_info)

    for _, name in enumerate(bone_lst):
        w, h, pivotx, pivoty, sx, sy = 0, 0, 0, 0, 1, 1
        info = bone_init_info[name]
        timeline = info['timeline']
        if not info['is_bone']:
            img_config = folder_file_map[timeline['folder']][timeline['file']]
            w, h = img_config['width'], img_config['height']
            pivotx, pivoty = img_config['pivotx'], img_config['pivoty']


        fx = timeline['x'] or 0
        fy = timeline['y'] or 0

        p = parent[name]

        if not info.has_key('children') or len(info['children']) == 0:
            sx = timeline['scalex'] == None and 1 or timeline['scalex']
            sy = timeline['scaley'] == None and 1 or timeline['scaley']

            while bone_init_info.has_key(p):
                pinfo = bone_init_info[p]
                ptimeline = pinfo['timeline']
                psx = ptimeline['scalex'] == None and 1 or ptimeline['scalex']
                psy = ptimeline['scaley'] == None and 1 or  ptimeline['scaley']

                fx = fx * psx
                fy = fy * psy

                sx *= psx
                sy *= psy
                p = parent[p]

        elif bone_init_info.has_key(p):
                parent_timeline = bone_init_info[p]['timeline']
                fx = fx * (parent_timeline['scalex'] == None and 1 or parent_timeline['scalex'])
                fy = fy * (parent_timeline['scaley'] == None and 1 or parent_timeline['scaley'])

        angle = timeline['angle'] or 0
        x, y, angle = calcPosAndRotation(w, h, pivotx, pivoty, fx, fy, angle, sx, sy)

        # also save to bone init info
        info['x'] = x
        info['y'] = y 
        info['angle'] = angle
        info['sx'] = sx
        info['sy'] = sy

        # save origin scale info
        info['osx'] = timeline['scalex'] == None and 1 or timeline['scalex']
        info['osy'] = timeline['scaley'] == None and 1 or timeline['scaley']

        bone_data = {
            'name': name,
            'parent': parent[name],
            'length': info['length'],
            'x': round(x, 2),
            'y': round(y, 2),
            'scaleX': sx,
            'scaleY': sy,
            'rotation': angle,
            #'transform': 'noScale'
        }

        bones.append(bone_data)

    return True   

def merge_parent(parent, local_parent, bone_length, bone_init_info, timeline_obj_key, name2timeline, name2zindex):
    visited = {}
    k_stack = []

    for k in local_parent.keys():
        if visited.has_key(k): continue

        cur_k = k
        while True:
            k_stack.append(cur_k)
            visited[cur_k] = True
            cur_k = local_parent[cur_k] 
            if not cur_k: break

        prefix = 'root'
        while len(k_stack):
            cur_k = k_stack.pop()
            next_prefix = '%s-%s' % (prefix, cur_k)
            parent[next_prefix] = prefix
            timeline_obj_key[name2timeline[cur_k]['id']] = next_prefix
            if not bone_init_info.has_key(next_prefix):
                bone_name = name2timeline[cur_k]['name']
                is_bone = name2timeline[cur_k]['is_bone']
                bone_init_info[next_prefix] = {
                    'length': is_bone and bone_length[bone_name] or 0,
                    'timeline': name2timeline[cur_k]['kfrms'][0],
                    'is_bone': is_bone,
                    'z_index': is_bone and -1 or name2zindex[cur_k],
                    'parent': prefix
                }
            prefix = next_prefix


def check_hierarchy_animation(key_datas):
    h_info = {}
    
    for key_id, key in key_datas.items():
        for k, v in key['bone_ref'].items():
            if not h_info.has_key(v['timeline_id']):
                h_info[v['timeline_id']] = v['parent']
                continue
            if h_info[v['timeline_id']] != v['parent']:
                return (False, 'mainline id(%s) time: %f bone_ref id(%s): bone hierarchy inconsistent!' % (key_id, key['time'], k))

        for k, v in key['obj_ref'].items():
            if not h_info.has_key(v['timeline_id']):
                h_info[v['timeline_id']] = v['parent']
                continue
            if h_info[v['timeline_id']] != v['parent']:
                return (False, 'mainline id(%s) time: %f object_ref(%s): bone hierarchy inconsistent!' % (key_id, key['time'], k))

    return (True, '')

def extract_slot_and_skin(slots, skins, folder_file_map, bone_init_info):
    for bone_name, info in bone_init_info.items():
        if info['is_bone']: continue

        timeline = info['timeline']
        img_config = folder_file_map[timeline['folder']][timeline['file']]
        w, h = img_config['width'], img_config['height']

        attachment_name = get_attachment_name(img_config['name'])
        slot_name = bone_name
        slot = {'attachment': attachment_name, 'bone': bone_name, 'name': slot_name}
        slots.append(slot)
        skins[slot_name] = {
            attachment_name: {
                'name': attachment_name,
                'width': w,
                'height': h
            }
        }

    # sort by default z_index
    slots.sort(key = lambda a: bone_init_info[a['bone']]['z_index'])

def check_and_fill_skin(skins, slot_name, attachment, img_config):
    if not attachment: return
    skins[slot_name] = skins.has_key(slot_name) and skins[slot_name] or {}
    skins[slot_name][attachment] = skins[slot_name].has_key(attachment) and skins[slot_name][attachment] or {
            'name': attachment,         
            'width': img_config['width'],
            'height': img_config['height']
    }

def set_bone_visible(bone_visible, time, key, visible):
    bone_visible[key] = bone_visible.has_key(key) and bone_visible[key] or []
    bone_visible[key].append((time, visible))

def check_bone_visible(bone_visible, time, key):
    if not bone_visible.has_key(key): return True
    visibles = bone_visible[key]
    for i in range(len(visibles) - 1, -1, -1):
        if time >= visibles[i][0]:
            return visibles[i][1]

    return True

def add_curve_info(data, curve_info):
    if not curve_info or not curve_info[0]: return
    curve, c1, c2, c3, c4 = curve_info[0], curve_info[1], curve_info[2], curve_info[3], curve_info[4]
    if curve == 'instant':
        data['curve'] = 'stepped'
    elif curve == 'bezier':
        data['curve'] = c1
        data['c2'] = c2
        data['c3'] = c3
        data['c4'] = c4

def record_key_frm_action(acts, ms_time, key, bone_init_info, act_type, arg):
    time = calc_spine_time(ms_time)

    if act_type == 'draw_order':
        acts['drawOrder'] = acts.has_key('drawOrder') and acts['drawOrder'] or []
        is_exist = False

        for _, v in enumerate(acts['drawOrder']):
            if abs(v['time'] - time) > sys.float_info.epsilon: continue
            if arg:
                v['offsets'] = v.has_key('offsets') and v['offsets'] or []
                v['offsets'].append({'offset': arg, 'slot': key})
            is_exist = True

        if not is_exist:
            draw_order = {'time': time}
            if arg:
                draw_order['offsets'] = [{'offset': arg, 'slot': key}]
            acts['drawOrder'].append(draw_order)

    elif act_type == 'attachment':
         acts['slots'] = acts.has_key('slots') and acts['slots'] or {}
         acts['slots'][key] = acts['slots'].has_key(key) and acts['slots'][key] or {}
         acts['slots'][key]['attachment'] = acts['slots'][key].has_key('attachment') and acts['slots'][key]['attachment'] or []
         acts['slots'][key]['attachment'].append({'time': time, 'name': arg})

    elif act_type == 'alpha':
         info = bone_init_info[key]
         alpha = arg
         if info['is_bone']:
             print '[WARNING] Unsupported bone alpha setting: name(%s) time(%f)' % (key, alpha)
             return

         data = {'time': time, 'color': hex(0xffffff00 | int(255 * alpha))[2:-1]}
         
         acts['slots'] = acts.has_key('slots') and acts['slots'] or {}
         acts['slots'][key] = acts['slots'].has_key(key) and acts['slots'][key] or {}
         acts['slots'][key]['color'] = acts['slots'][key].has_key('color') and acts['slots'][key]['color'] or []
         acts['slots'][key]['color'].append(data)

    elif act_type == 'translate':
         acts['bones'] = acts.has_key('bones') and acts['bones'] or {}
         acts['bones'][key] = acts['bones'].has_key(key) and acts['bones'][key] or {}
         acts['bones'][key]['translate'] = acts['bones'][key].has_key('translate') and acts['bones'][key]['translate'] or []

         x, y, curve_info = arg[0], arg[1], arg[2]
         bx, by = bone_init_info[key]['x'], bone_init_info[key]['y']
         data = {'time': time, 'x': round(x - bx, 2), 'y': round(y - by, 2)}
         add_curve_info(data, curve_info)

         acts['bones'][key]['translate'].append(data)

    elif act_type == 'rotate':
         acts['bones'] = acts.has_key('bones') and acts['bones'] or {}
         acts['bones'][key] = acts['bones'].has_key(key) and acts['bones'][key] or {}
         acts['bones'][key]['rotate'] = acts['bones'][key].has_key('rotate') and acts['bones'][key]['rotate'] or []
         bangle = bone_init_info[key]['angle']

         angle, curve_info = arg[0], arg[1]
         data = {'time': time, 'angle': angle - bangle}
         add_curve_info(data, curve_info)

         acts['bones'][key]['rotate'].append(data)

    elif act_type == 'scale':
         acts['bones'] = acts.has_key('bones') and acts['bones'] or {}
         acts['bones'][key] = acts['bones'].has_key(key) and acts['bones'][key] or {}
         acts['bones'][key]['scale'] = acts['bones'][key].has_key('scale') and acts['bones'][key]['scale'] or []

         x, y, curve_info = arg[0], arg[1], arg[2]
         bx, by = bone_init_info[key]['sx'], bone_init_info[key]['sy']

         data = {'time': time, 'x': round(x / bx, 2), 'y': round(y / by, 2)}
         add_curve_info(data, curve_info)

         acts['bones'][key]['scale'].append(data)

def fix_draw_order_acts(acts, default_draw_order):
    if not acts.has_key('drawOrder'): return

    draw_orders = acts['drawOrder']

    for order_act in draw_orders:
        if not order_act.has_key('offsets'): continue

        offsets = order_act['offsets']
        offsets.sort(key = lambda s: default_draw_order[s['slot']])


def sort_key_frm_actions(acts):
    if acts.has_key('drawOrder'):
        acts['drawOrder'].sort(key = lambda a: a['time'])

    if acts.has_key('slots'):
        for v in acts['slots'].values():
            if v.has_key('attachment'): v['attachment'].sort(key = lambda a: a['time'])
            if v.has_key('color'): v['color'].sort(key = lambda a: a['time'])

    if acts.has_key('bones'):
        for v in acts['bones'].values():
            if v.has_key('translate'): v['translate'].sort(key = lambda a: a['time'])
            if v.has_key('rotate'): v['rotate'].sort(key = lambda a: a['time'])
            if v.has_key('scale'): v['scale'].sort(key = lambda a: a['time'])

def optimal_default_act(act, default_act):
    if not default_act: return
    for k, v in act.items(): 
        if k == 'time': continue
        if not default_act.has_key(k): return
        if default_act[k] != v: return

    for k , v in default_act.items():
        del act[k]

def remove_unnecessary_action(actions, default_act):
    if not len(actions): return

    lst_act = actions[0]
    idx = 1

    has_repeat = False
    for i, act in enumerate(actions):
        if act['time'] == lst_act['time']:
            continue

        is_diff = False
        for k, v in act.items():
            if k != 'time' and (not lst_act.has_key(k) or lst_act[k] != v):
                is_diff = True
                break

        lst_act = act

        if is_diff:
            if has_repeat:
                actions[idx] = actions[i - 1]
                idx += 1
                
            actions[idx] = act
            has_repeat = False
            idx += 1
        else:
            has_repeat = True
        

    length = len(actions)
    for i in range(length - 1, idx - 1, -1):
        del actions[i]

    for i, act in enumerate(actions):
        optimal_default_act(act, default_act)


DEFAULT_ACTION_DICT = {
    'drawOrder': None,
    'attachment': None,
    'color': None,
    'translate':  {'x': 0, 'y': 0},
    'rotate': {'angle': 0},
    'scale': {'x': 1, 'y': 1}
}
def optimal_animation_data(acts):
    if acts.has_key('slots'):
        for v in acts['slots'].values():
            if v.has_key('attachment'): remove_unnecessary_action(v['attachment'], DEFAULT_ACTION_DICT['attachment'])
            if v.has_key('color'): remove_unnecessary_action(v['color'], DEFAULT_ACTION_DICT['color'])
    if acts.has_key('bones'):
        for v in acts['bones'].values():
            if v.has_key('translate'): remove_unnecessary_action(v['translate'], DEFAULT_ACTION_DICT['translate'])
            if v.has_key('rotate'): remove_unnecessary_action(v['rotate'], DEFAULT_ACTION_DICT['rotate'])
            if v.has_key('scale'): remove_unnecessary_action(v['scale'], DEFAULT_ACTION_DICT['scale'])
    

def check_and_fill_ani_action(datas, end_time, is_looping):
    if datas[-1]['time'] == 0 or datas[-1]['time'] == end_time:
        return
    
    fill_data = dict(is_looping and datas[0] or datas[-1])
    fill_data['time'] = end_time
    datas.append(fill_data)

def fill_ani_time(acts, end_time, is_looping):
    end_time = calc_spine_time(end_time)
    if acts.has_key('slots'):
        for v in acts['slots'].values():
            if not v.has_key('color'): continue
            check_and_fill_ani_action(v['color'], end_time, is_looping)

    if acts.has_key('bones'):
        for v in acts['bones'].values():
            if v.has_key('translate'):
                check_and_fill_ani_action(v['translate'], end_time, is_looping)
            if v.has_key('rotate'):
                check_and_fill_ani_action(v['rotate'], end_time, is_looping)
            if v.has_key('scale'):
                check_and_fill_ani_action(v['scale'], end_time, is_looping)

def extract_animations(anis, slots, skins, entity, folder_file_map, bone_init_info, ani_timeline_obj_key):
    default_draw_order = {}
    for i, slot in enumerate(slots):
        default_draw_order[slot['name']] = i

    for _, ani in enumerate(entity['anis']):
        acts = {}
        anis[ani['name']] = acts

        timeline_obj_key = ani_timeline_obj_key[ani['name']]
        last_order = {}
        bone_visible = {}

        keys = ani['key'].values()
        keys.sort(key = lambda k: k['time'])

        for k in keys:
            showed_slot = {}
            time = k['time']
            for bone_ref in k['bone_ref'].values():
                bone_name = timeline_obj_key[bone_ref['timeline_id']]

            has_order_changed = False
            for obj_ref in k['obj_ref'].values():  
                slot_name = timeline_obj_key[obj_ref['timeline_id']]
                showed_slot[slot_name] = True
                set_bone_visible(bone_visible, time, slot_name, True)

                if last_order.has_key(slot_name):
                    if last_order[slot_name] != obj_ref['z_index']:
                        has_order_changed = True
                elif default_draw_order[slot_name] != obj_ref['z_index']:
                    has_order_changed = True

                last_order[slot_name] = obj_ref['z_index']

            if has_order_changed:
                for obj_ref in k['obj_ref'].values():  
                    slot_name = timeline_obj_key[obj_ref['timeline_id']]
                    record_key_frm_action(acts, time, slot_name, bone_init_info, 'draw_order', obj_ref['z_index'] - default_draw_order[slot_name])

            for slot_name, info in bone_init_info.items():
                if showed_slot.has_key(slot_name): continue
                if info['is_bone']: continue
                set_bone_visible(bone_visible, k['time'], slot_name, False)
                record_key_frm_action(acts, k['time'], slot_name, bone_init_info, 'attachment', '')


        # fix draw order action expression, to compatible spine 
        fix_draw_order_acts(acts, default_draw_order)

        bone_time_state = {}
        for t in ani['timelines'].values():
            key = timeline_obj_key[t['id']]
            kfrms =  t['kfrms']
            bone_time_state[key] = []
            states = bone_time_state[key]
            for i, kfrm in enumerate(kfrms):
                time = kfrm['time']
                sx = kfrm['scalex'] == None and 1 or kfrm['scalex']
                sy = kfrm['scaley'] == None and 1 or kfrm['scaley']
                states.append({
                    'sx': sx,
                    'sy': sy,
                    'time': time
                })

        # TODO: fix bone scale animation. - 2020.09.03
        
        last_attachment = {}
        for t in ani['timelines'].values():
            key = timeline_obj_key[t['id']]
            kfrms =  t['kfrms']
            len_kfrms = len(kfrms)
            info = bone_init_info[key]

            for i, kfrm in enumerate(kfrms):
                w, h, pivotx, pivoty, sx, sy = 0, 0, 0, 0, 1, 1
                time = kfrm['time']

                if not check_bone_visible(bone_visible, time, key): continue

                if kfrm['file']:
                    img_config = folder_file_map[kfrm['folder']][kfrm['file']]
                    w, h = img_config['width'], img_config['height']
                    pivotx, pivoty = img_config['pivotx'], img_config['pivoty']
                    attachment_name = get_attachment_name(img_config['name'])
                    if (not last_attachment.has_key(key)\
                        or attachment_name != last_attachment[key]):

                        record_key_frm_action(acts, time, key, bone_init_info, 'attachment', attachment_name)
                        # if no this attachment, fill it.
                        check_and_fill_skin(skins, key, attachment_name, img_config)
                        last_attachment[key] = attachment_name

                sx = 1
                sy = 1
                fx = kfrm['x'] or 0
                fy = kfrm['y'] or 0

                p = info['parent']
                states = bone_time_state.has_key(p) and bone_time_state[p] or []

                if not info.has_key('children') or len(info['children']) == 0:
                    sx = kfrm['scalex'] == None and 1 or kfrm['scalex']
                    sy = kfrm['scaley'] == None and 1 or kfrm['scaley']

                    while bone_init_info.has_key(p):
                        states = bone_time_state[p]
                        psx, psy = find_scales_in_keyfrm_state(time, states, bone_init_info[p]['osx'], bone_init_info[p]['osy'])

                        fx = fx * psx
                        fy = fy * psy

                        sx *= psx
                        sy *= psy
                        p = bone_init_info[p]['parent']
                elif bone_init_info.has_key(p):
                        psx, psy = find_scales_in_keyfrm_state(time, states, bone_init_info[p]['osx'], bone_init_info[p]['osy'])
                        fx = fx * psx
                        fy = fy * psy

                angle = kfrm['angle'] or 0
                x, y, angle = calcPosAndRotation(w, h, pivotx, pivoty, fx, fy, angle, sx, sy)
                
                curve_info = None
                if kfrm['curve']:
                    if kfrm['curve'] == 'cubic':
                        print '[WARNING] Unsupported curve type \'1d Speed Curve\': ani name(%s) time(%f) timeline(%s)' % (ani['name'], time, t['name'])
                    else:
                        curve_info = (kfrm['curve'], kfrm['c1'], kfrm['c2'], kfrm['c3'], kfrm['c4'])

                record_key_frm_action(acts, time, key, bone_init_info, 'translate', (x, y, curve_info))
                record_key_frm_action(acts, time, key, bone_init_info, 'rotate', (angle, curve_info))
                record_key_frm_action(acts, time, key, bone_init_info, 'scale', (sx, sy, curve_info))

                if not bone_init_info[key]['is_bone']:
                    if i < len_kfrms - 1 and kfrm['alpha'] != kfrms[i + 1]['alpha'] and kfrm['curve']:
                        print '[WARNING] Unsupported animation curve to \'alpha\': ani name(%s) time(%f) timeline(%s)' % (ani['name'], time, t['name'])

                    record_key_frm_action(acts, time, key, bone_init_info, 'alpha', kfrm['alpha'] == None and 1 or kfrm['alpha'])

        # sort actions by time
        sort_key_frm_actions(acts)
        # optimal_animation_data 
        optimal_animation_data(acts)
        # fill ani key frame to end time
        fill_ani_time(acts, ani['length'], ani['looping'])
    

def output_entity2spine(entity, folder_file_map, out_folder, out_name):
    spine_obj = gen_spine_obj(entity['name'])
    extract_skeleton_data(spine_obj['skeleton'], entity)

    bone_init_info = {}
    ani_timeline_obj_key = {}
    if not extract_bone_data(spine_obj['bones'], entity, folder_file_map, bone_init_info, ani_timeline_obj_key):
        # extract failed
        return

    extract_slot_and_skin(spine_obj['slots'], spine_obj['skins'][0]['attachments'], folder_file_map, bone_init_info)
    extract_animations(spine_obj['animations'], spine_obj['slots'], spine_obj['skins'][0]['attachments'], entity, folder_file_map, bone_init_info, ani_timeline_obj_key)
    
    file_name = "%s-%s.%s" % (out_name, entity['name'], SPINE_EXT)
    output_path = os.path.join(out_folder, file_name)
    write_json(spine_obj, output_path)
    print '[INFO] Converted entity: %s to %s' % (entity['name'], output_path)


def convert2spine(entities, folder_file_map, out_folder, out_name):
    # For simplicity, we treat every entity as a single spine animation.
    for _, entity in enumerate(entities):
        output_entity2spine(entity, folder_file_map, out_folder, out_name)

def convert(in_path, out_folder, out_name):
    print '[INFO] Converting...: %s' % (in_path)
    entities, folder_file_map = extract_spriter_data(in_path)
    convert2spine(entities, folder_file_map, out_folder, out_name)

def makedir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise

def main(in_path, out_path):
    if not os.path.exists(in_path):
        print '[ERROR] \'input path\': %s unexist!' % (in_path)
        return

    print '[INFO] Start convert: %s => %s' % (in_path, out_path)

    if not os.path.isdir(in_path):
        file_name = None
        if os.path.isdir(out_path) or out_path.endswith('/') or out_path.endswith('\\'):
            if not os.path.exists(out_path):
                makedir_p(out_path)

            file_name = os.path.splitext(os.path.basename(in_path))[0]
        else:
            file_name = os.path.splitext(os.path.basename(out_path))[0]
            out_path = os.path.dirname(out_path)

        convert(in_path, out_path, file_name)


    for root, dirs, files in os.walk(in_path):
        out_folder = os.path.join(out_path, re.sub(r'^[\\/]', '', root.replace(in_path, '')))

        if not os.path.exists(out_folder):
            makedir_p(out_folder)

        for f in files:
            if not f.lower().endswith('.scml'): continue
            in_file = os.path.join(root, f)
            out_file = os.path.splitext(f)[0]
            convert(in_file, out_folder, out_file)

    print '[INFO] End convert!'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A simple converter that use for spriter file convert to spine file.')
    parser.add_argument('-i', type=str, dest='in_path', help='Directory or File to be converted. By default, point to the current directory.')
    parser.add_argument('-o', type=str, dest='out_path', help='Directory or File convert to. By default, point to the current directory.')
    args = parser.parse_args()

    main(args.in_path or './', args.out_path or './')
