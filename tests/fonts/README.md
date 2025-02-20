## Testing fonts

The fonts are included here for testing and some have been modified. If you wish to use these fonts
for other purposes, it is recommended that you download them from the original source, not from here.

Original sources:
* `4x6.bdf`
  - https://www.cl.cam.ac.uk/~mgk25/ucs-fonts.html
  - in the public domain
* `6x13.fon`
  - https://www.chiark.greenend.org.uk/~sgtatham/fonts/
  - in the public domain
* `WebbySmall.fon` and `WebbySmall.pcf`
  - https://github.com/bluescan/proggyfonts/tree/master/ProggyOriginal
  - (c) 2004, 2005 Tristan Grimmer, released under an MIT licence
* `wbfont`
  - http://aminet.net/text/bfont/wbfont.lha
  - (c) 1999 Keith Halstead, free to distribute so long as the readme file is included
* `L2UNIVB18.FNT`
  - http://cd.textfiles.com/geminiatari/FILES/FONTS/GDOS/TWFNTSLA/
  - Bernie LaGrave / Ric Kalford
  - in the public domain
* `AI360GVP.VGA`
  - supplied with the GEM/3 screen drivers
  - http://www.deltasoft.com/downloads/screendr.zip
  - GNU General Public License v2
* `times.nlq` and `daisy.nlq`
  - distributed with Roy Goldman's Daisy-Dot III
  - in the public domain
* `cmbx10.120pk`
  - https://www.ctan.org/pkg/cm
  - unmodified bitmap of the Computer Modern font created by Donald Knuth
  - released under his usual licence: https://ctan.org/license/knuth
* `SHILLING.cvt.gz`
  - https://www.commodore.ca/manuals/funet/cbm/geos/graphics/fonts/unsorted/
  - Symbol font created by Dick Estel - copyright 1989 - released for free use
* `Alpha-2B.pdb`
  - http://www.rainerzenz.de/palm/alphafonts.html
  - © 2000/2001 for Alpha Font Collection: Rainer Zenz. If you want to substitute one of
    these fonts to shareware or commercial software, please contact me. For freeware
    it's free, of course. If you want to publish it - do it! But have a look at
    PalmGear for the latest version.
* `WARPSANS.FON`
  - http://www.altsan.org
  - The WarpSans Extended Sizes may be freely used, redistributed, and/or
    modified, by any individual, group or organization, for any purpose.  
    (C) 2013 Alexander Taylor
* `hershey-az.jhf`
   - first 26 lines of `hersh.oc1` from Peter Holzmann's USENET distribution of the Hershey fonts
   - see e.g. https://www.galleyrack.com/hershey/additional-fonts-for-VARKON/hershey/index.html
   - The Hershey Fonts were originally created by Dr. A. V. Hershey
   - See README for conditions

### Derivatives of `4x6`

* `4x6.yaff` was created from `4x6.bdf` using `monobit`
* `4x6.psf` was created from `4x6.yaff` using `monobit`
* `4x6.fzx` was created from `4x6.bdf` using `monobit`
* `4x6.c` was created from `4x6.yaff` using `monobit`
* `4x6.dfont` and `4x6.bin` were created from `4x6.bdf` using `ufond` (part of `fondu`)
* `4x6.vfont*` were created from `4x6.psf` using `psftools` v1.1.1
* `4x6-ams.com*` were created from `4x6.psf` using `psftools` v1.1.1
* `4x6.ttf` was created from `4x6.bdf` using `fonttosfnt`
* `4x6.otb`, `4x6.sfnt.dfont` and `4x6.ffms.ttf` were created from `4x6.bdf` using FontForge
* `8x8.bbc` was created from `4x6.psf` using `psftools` v1.1.1
* `8x16.hex` was created from `4x6.yaff` using `bittermelon`
* `8x16.draw` was created from `8x16.hex` using `hexdraw`
* `8x16-*.cpi` were created from `8x16.hex` through a PSF intermediate using `monobit` and `psftools`
* `8x16.cp` was extracted from `8x16.cpi` using `codepage -a` and `tail -c 8257`
* `8x16.f16` was created from `8x16.cp` using `monobit`
* `8X16.XB`, `8X16-FRA.COM` and `8X16-TSR.COM` were created from `8x16.f16` using Fontraption
* `8X16-FE.COM` was created from `8X16-FRA.COM` using `FONTEDIT`
* `8X16-REX.COM` was created from `8X16-FRA.COM` using Font Mania 2.2


### Derivatives of `6x13`

* `6x13.fnt` was extracted from `6x13.fon` using `tail -c +449`
* `6x13.dec` was created from `6x13.fnt` using `monobit`
* `6x13.bmf/6x13-json.fnt` was manually converted from `6x13-xml.fnt`
* the other files in `6x13.bmf` were created with Angelcode BMFont


### Derivatives of WebbySmall:

* `webby-small-kerned.yaff` was created from `WebbySmall.pcf` using `pcf2bdf` and `monobit`
  and manually edited to add some kerning and remove non-ascii glyphs.


### Derivatives of Hershey Fonts:
* `hershey.yaff`, `hershey.svg` and `hershey.fon` were created from `hershey-az.jhf` using `monobit`
