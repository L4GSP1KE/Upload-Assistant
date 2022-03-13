import vapoursynth as vs
core = vs.core
from awsmfunc import ScreenGen, DynamicTonemap, FrameInfo, zresize
import random
import argparse
from typing import Union, List
from pathlib import Path
import os, sys
from functools import partial

# Modified version of https://git.concertos.live/AHD/ahd_utils/src/branch/master/screengn.py
def vs_screengn(source, encode, filter_b_frames, num, dir):
    # prefer ffms2, fallback to lsmash for m2ts
    if str(source).endswith(".m2ts"):
        src = core.lsmas.LWLibavSource(source)
    else:
        src = core.ffms2.Source(source, cachefile=f"{os.path.abspath(dir)}{os.sep}ffms2.ffms2")

    # we don't allow encodes in non-mkv containers anyway
    if encode:
        enc = core.ffms2.Source(encode)

    # since encodes are optional we use source length
    num_frames = len(src)
    # these values don't really matter, they're just to cut off intros/credits
    start, end = 1000, num_frames - 10000

    # filter b frames function for frameeval
    def filter_ftype(n, f, clip, frame, frames, ftype="B"):
        if f.props["_PictType"].decode() == ftype:
            frames.append(frame)
        return clip

    # generate random frame numbers, sort, and format for ScreenGen
    # if filter option is on filter out non-b frames in encode
    frames = []
    if filter_b_frames:
        with open(os.devnull, "wb") as f:
            i = 0
            while len(frames) < num:
                frame = random.randint(start, end)
                enc_f = enc[frame]
                enc_f = enc_f.std.FrameEval(partial(filter_ftype, clip=enc_f, frame=frame, frames=frames), enc_f)
                enc_f.output(f)
                i += 1
                if i > num * 10:
                    raise ValueError("screengn: Encode doesn't seem to contain desired picture type frames.")
    else:
        for _ in range(num):
            frames.append(random.randint(start, end))
    frames = sorted(frames)
    frames = [f"{x}\n" for x in frames]

    # write to file, we might want to re-use these later
    with open("screens.txt", "w") as txt:
        txt.writelines(frames)

    # if an encode exists we have to crop and resize
    if encode:
        if src.width != enc.width and src.height != enc.height:
            ref = zresize(enc, preset=src.height)
            crop = [(src.width - ref.width) / 2, (src.height - ref.height) / 2]
            src = src.std.Crop(left=crop[0], right=crop[0], top=crop[1], bottom=crop[1])
            if enc.width / enc.height > 16 / 9:
                width = enc.width
                height = None
            else:
                width = None
                height = enc.height
            src = zresize(src, width=width, height=height)

    # tonemap HDR
    tonemapped = False
    if src.get_frame(0).props["_Primaries"] == 9:
        tonemapped = True
        src = DynamicTonemap(src, src_fmt=False, libplacebo=False, adjust_gamma=True)
        if encode:
            enc = DynamicTonemap(enc, src_fmt=False, libplacebo=False, adjust_gamma=True)

    # add FrameInfo
    if tonemapped == True:
        src = FrameInfo(src, "Tonemapped")
    ScreenGen(src, dir, "a")
    if encode:
        if tonemapped == True:
            enc = FrameInfo(enc, "Encode (Tonemapped)")
        ScreenGen(enc, dir, "b")