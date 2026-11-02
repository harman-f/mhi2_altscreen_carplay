#!/usr/bin/env python3
"""Exact full-byte SKG13 Skin3 reconstruction, OFFLINE ONLY.

Source: official M.I.B. ImageMod at pinned commit; Skin3 is stock Skin1
with its pinned delta, not stock Skin0. Does NOT touch a Unit, install
resources, upload proprietary MCF, or claim actual installed skin.
"""
import argparse, hashlib, pathlib, subprocess, sys

SOURCE_SHA256="3d0e0498492b68fa8b6529ff23060fe387d349bf8a9a1b404cdd3b1c617bb6e0"
DELTA_GIT_BLOB_SHA1="d43b48bbfd4f9a4dd3529d6ce2681719e32ef88a"
DELTA_SIZE=10036885
OFFICIAL_IMAGE_MOD_BLOB_SHA1="01cde56a2673bed8a4d1d623e1ec5feeacb32d89"
RESULT_SIZE=30758884
RESULT_SHA1="0a322d581cb320c60bc6be87e2817fcdf20aa2f2"
RESULT_SHA256="0cd5623541b32eb865716eadd86f978c018797f2b2be83d00289c3f1090886e4"

def sha(data,alg): return hashlib.new(alg,data).hexdigest()
def gitsha(data): return sha(b"blob "+str(len(data)).encode("ascii")+bytes([0])+data,"sha1")
def validate(base,delta,out,image_mod):
    for p in (base,delta,image_mod):
        if not p.is_file(): raise ValueError("INPUT_MISSING "+str(p))
    source=base.read_bytes()
    if len(source)!=29964332 or sha(source,"sha256")!=SOURCE_SHA256: raise ValueError("STOCK_SKIN1_HASH_MISMATCH")
    patch=delta.read_bytes()
    if len(patch)!=DELTA_SIZE or gitsha(patch)!=DELTA_GIT_BLOB_SHA1: raise ValueError("OFFICIAL_DELTA_BLOB_MISMATCH")
    mod=image_mod.read_bytes()
    if gitsha(mod)!=OFFICIAL_IMAGE_MOD_BLOB_SHA1: raise ValueError("OFFICIAL_IMAGEMOD_BLOB_MISMATCH")
    for term in (b"cp -crf $IMGDIR/skin1/view/* $IMGDIR/skin3/view/",
                 b"cp -crf $IMGDIR/skin1/viewhandler.zip $IMGDIR/skin3/",
                 b"cp -crf $IMGDIR/skin1/images.mcf $IMGDIR/skin3/",
                 b"$RDIFF -f patch $IMGDIR/skin3/images.mcf"):
        if term not in mod: raise ValueError("SKIN3_CLASS_COPY_RULE_CHANGED")
    if out.exists(): raise ValueError("REFUSE_OUTPUT_OVERWRITE")
    try:
        subprocess.run(["rdiff","-f","patch",str(base),str(delta),str(out)],check=True)
        result=out.read_bytes()
        if len(result)!=RESULT_SIZE or sha(result,"sha1")!=RESULT_SHA1 or sha(result,"sha256")!=RESULT_SHA256:
            raise ValueError("SKIN3_FULL_BINARY_HASH_MISMATCH")
        print("SKIN3_FULL_MCF_RECONSTRUCTION_PASS bytes=%s sha1=%s sha256=%s source=PINNED_SKIN1_DELTA"%
              (len(result),RESULT_SHA1,RESULT_SHA256))
    finally:
        # No original/derivative proprietary MCF output survives the CI job.
        if out.exists(): out.unlink()

if __name__=="__main__":
    a=argparse.ArgumentParser()
    for x in ("base","delta","output","image-mod"): a.add_argument("--"+x,required=True,type=pathlib.Path)
    p=a.parse_args()
    validate(p.base,p.delta,p.output,p.image_mod)
