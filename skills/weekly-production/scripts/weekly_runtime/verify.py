# SPDX-License-Identifier: GPL-3.0-only
"""Inspect actual export streams, work boundaries and the encoded music track."""
import argparse
import json
from pathlib import Path
import sys
import wave
import av
import numpy as np
from PIL import Image, ImageOps
from .common import atomic_json

def check(condition, detail='成片验证失败'):
    if not condition:
        raise ValueError(str(detail))

def frame_at(container, seconds):
    stream = container.streams.video[0]
    container.seek(max(0, int(seconds / stream.time_base)), stream=stream, backward=True)
    for frame in container.decode(stream):
        if frame.time >= seconds - 0.0001:
            return frame.to_image()
    raise ValueError('视频在检查时间点缺帧')

def verify(out, target_override=None):
    out = Path(out)
    program = json.loads((out / 'program.json').read_text('utf-8'))
    media = json.loads((out / 'media.json').read_text('utf-8'))
    capture = json.loads((out / 'capture-report.json').read_text('utf-8'))
    target = Path(target_override) if target_override is not None else out / 'program.mp4'
    qa = out / 'qa'
    qa.mkdir(exist_ok=True)
    report = {'path': str(target), 'publication': program['publication'], 'boundaries': [], 'plates': [], 'music': {}, 'motion': {}}
    with av.open(str(target)) as actual:
        video, audio = (actual.streams.video[0], actual.streams.audio[0])
        report['streams'] = {'width': video.width, 'height': video.height, 'fps': str(video.average_rate), 'frames': video.frames, 'video_seconds': float(video.duration * video.time_base), 'audio_seconds': float(audio.duration * audio.time_base), 'sample_rate': audio.rate, 'channels': audio.codec_context.layout.nb_channels, 'bytes': target.stat().st_size}
        spec = report['streams']
        check((spec['width'], spec['height'], spec['frames']) == (1920, 1080, program['total_frames']), '成片验证失败')
        check(float(video.average_rate) == 30, '成片验证失败')
        check(abs(spec['video_seconds'] - program['duration']) < 1 / 30, '成片验证失败')
        check(abs(spec['audio_seconds'] - program['duration']) < 0.025, '成片验证失败')
        check((spec['sample_rate'], spec['channels']) == (48000, 2), '成片验证失败')
        for scene in program['scenes']:
            if scene['template'] not in ('ranking', 'podium'):
                continue
            bvid = scene['row']['bvid']
            with av.open(str(Path(media[bvid]['path']))) as source:
                stream = source.streams.video[0]
                resolution = [stream.width, stream.height]
                for label, position in (('start', 0.2), ('end', scene['duration'] - 0.2)):
                    reference = frame_at(source, position)
                    picture = frame_at(actual, scene['start'] + position)
                    framed = scene['template'] == 'ranking' or position < scene.get('data_seconds', 7)
                    if framed:
                        picture = picture.crop((44, 184, 1444, 972))
                    size = picture.size
                    expected = Image.new('RGB', size, (27, 41, 53) if framed else (0, 0, 0))
                    scaled = ImageOps.contain(reference, size, Image.Resampling.BICUBIC)
                    expected.paste(scaled, ((size[0] - scaled.width) // 2, (size[1] - scaled.height) // 2))
                    a = np.asarray(picture.convert('L').resize((160, 90)), dtype=float)
                    b = np.asarray(expected.convert('L').resize((160, 90)), dtype=float)
                    error = float(np.mean(np.abs(a - b)))
                    report['boundaries'].append({'bvid': bvid, 'rank': scene['row']['rank'], 'edge': label, 'source_resolution': resolution, 'mae': round(error, 4), 'mode': 'window' if framed else 'fullscreen'})
                    check(error < 12, (bvid, label, error))
        for template in ('chapter', 'next', 'podium_reveal', 'news_chapter'):
            scene = next((s for s in program['scenes'] if s['template'] == template), None)
            if scene is None:
                continue
            a = frame_at(actual, scene['start'] + 2 / 30).convert('L').resize((320, 180))
            b = frame_at(actual, scene['start'] + scene['duration'] * 0.55).convert('L').resize((320, 180))
            difference = float(np.mean(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))))
            report['motion'][template] = {'mae': round(difference, 3)}
            check(difference > 5, (template, difference))
        for scene in program['scenes']:
            position = min(0.5, scene['duration'] / 2)
            if scene.get('animation'):
                frame_index = int(position * scene['animation']['fps'])
                position = frame_index / scene['animation']['fps']
                plate = out / 'motion' / scene['id'] / f'frame-{frame_index + 1:04d}.png'
            else:
                plate = out / 'plates' / (scene['id'] + '.png')
            actual_picture = frame_at(actual, scene['start'] + position)
            with Image.open(plate) as expected_picture:
                boxes = [(1460, 140, 1880, 970), (44, 978, 1880, 1040), (0, 0, 1920, 140)] if scene['template'] in ('ranking', 'podium') else [(0, 0, 1920, 1080)]
                errors = []
                for box in boxes:
                    a = np.asarray(actual_picture.crop(box).convert('L'), dtype=float)
                    b = np.asarray(expected_picture.crop(box).convert('L'), dtype=float)
                    errors.append(float(np.mean(np.abs(a - b))))
            error = max(errors)
            report['plates'].append({'id': scene['id'], 'template': scene['template'], 'mae': round(error, 4)})
            check(error < 8, (scene['id'], 'broadcast graphics differ from captured copy', error))
    windows = []
    for scene in program['scenes']:
        if scene['template'] in ('ranking', 'podium'):
            continue
        with wave.open(str(out / 'audio' / (scene['id'] + '.wav')), 'rb') as sound:
            reference = np.frombuffer(sound.readframes(sound.getnframes()), dtype='<i2').reshape(-1, 2).astype(np.float32) / 32768
        begin = round(scene['start'] * 48000)
        windows.append({'id': scene['id'], 'start': begin, 'begin': begin + 4800, 'end': begin + len(reference) - 4800, 'reference': reference, 'xy': 0.0, 'xx': 0.0, 'yy': 0.0, 'samples': 0})
    index = 0
    with av.open(str(target)) as actual:
        for frame in actual.decode(audio=0):
            start = round(float(frame.pts * frame.time_base) * 48000)
            values = frame.to_ndarray().T
            end = start + len(values)
            while index < len(windows) and windows[index]['end'] <= start:
                index += 1
            cursor = index
            while cursor < len(windows) and windows[cursor]['begin'] < end:
                window = windows[cursor]
                lo, hi = (max(start, window['begin']), min(end, window['end']))
                if hi > lo:
                    x = values[lo - start:hi - start].astype(np.float64)
                    y = window['reference'][lo - window['start']:hi - window['start']].astype(np.float64)
                    window['xy'] += float(np.sum(x * y))
                    window['xx'] += float(np.sum(x * x))
                    window['yy'] += float(np.sum(y * y))
                    window['samples'] += hi - lo
                cursor += 1
    for window in windows:
        correlation = window['xy'] / max((window['xx'] * window['yy']) ** 0.5, 1e-09)
        report['music'][window['id']] = {'correlation': round(correlation, 6), 'samples': window['samples']}
        check(correlation > 0.98, (window['id'], correlation))
    report['graphics'] = {'scenes': len(capture['scenes']), 'catalogue': len(capture['catalogue']), 'motion_scenes': len(capture['motion']), 'motion_frames': sum((m['frames'] for m in capture['motion'])), 'overflow': sum((bool(s.get('overflow')) for s in capture['scenes'])), 'draft_marks': sum((bool(s.get('forbiddenText')) for s in capture['scenes'])), 'character_dialogue': sum((bool(s.get('characterDialogue')) for s in capture['scenes']))}
    check(report['graphics']['character_dialogue'] == 0, '成片验证失败')
    report['mastering'] = json.loads((out / 'audio/mastering.json').read_text('utf-8'))
    check(report['mastering']['peak_check_passed'] and report['mastering']['true_peak_dbtp'] <= -1, '成片验证失败')
    report['passed'] = True
    atomic_json(qa / 'verified-program.json', report)
    return report
