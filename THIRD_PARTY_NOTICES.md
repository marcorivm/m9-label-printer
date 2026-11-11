# Third-party software bundled in the app

The packaged app (the downloads on the Releases page) includes these programs,
each run as a separate process. They keep their own licences.

## jbigkit — `pbmtojbg`

JBIG1 compression, used to encode each print band.
Copyright Markus Kuhn. Licensed under the GNU General Public License,
version 2 or later. https://www.cl.cam.ac.uk/~mgk25/jbigkit/

The exact source the bundled binary was built from, `jbigkit-2.2.tar.gz`
(SHA-256 `3302109c93b7befbffa3cfe8bceb4355f19dea0ee7dcb5f33710b1648bf6645c`),
is attached to every release next to the app downloads, and includes the
full licence text (`COPYING`).

## blueutil (macOS app only)

Connects the Bluetooth link before printing and lists paired devices.
Originally written by Frederik Seiffert; Copyright (c) 2011-2026 Ivan Kuchin.
MIT licence. https://github.com/toy/blueutil

> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

## Python libraries

- **Pillow** — MIT-CMU licence (HPND). https://python-pillow.org
- **pypdfium2** — Apache-2.0 / BSD-3-Clause; bundles **PDFium** (BSD-3-Clause,
  Apache-2.0). https://github.com/pypdfium2-team/pypdfium2
- **Python** and **Tcl/Tk** — PSF licence and Tcl/Tk licence.
